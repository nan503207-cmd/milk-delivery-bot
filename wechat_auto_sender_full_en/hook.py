# -*- coding: utf-8 -*-
"""
hooks.py
核心流程：渲染模板 -> 校验/计算余额 -> 发送 -> 记账 -> 更新任务状态
被 scheduler 调用：process_one_task(task_id)
"""

import json
from decimal import Decimal
from pathlib import Path

# 轻量日志：优先用 loguru，否则退化到 print
try:
    from loguru import logger
except Exception:  # pragma: no cover
    class _L:
        def info(self, *a, **k): print("[INFO]", *a)
        def warning(self, *a, **k): print("[WARN]", *a)
        def error(self, *a, **k): print("[ERROR]", *a)
        def exception(self, *a, **k): print("[EXC]", *a)
    logger = _L()

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import TEMPLATE_DIR, DRY_RUN
from db_utils import (
    session_scope,
    recalc_subscription_balance,
    add_transaction,
    mark_task_status,
)
from models import Task

# 懒加载模板环境
_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(disabled_extensions=("j2",)),
)

def _render_template(key: str, payload: dict) -> str:
    """
    渲染 Jinja2 模板；根据 key 选择对应 .j2 文件
    """
    tpl_path = Path(TEMPLATE_DIR) / f"{key}.j2"
    if not tpl_path.exists():
        raise FileNotFoundError(f"Template not found: {tpl_path}")
    tpl = _env.get_template(f"{key}.j2")
    return tpl.render(**payload)

def _payload(task: Task) -> dict:
    if not task.payload_json:
        return {}
    try:
        return json.loads(task.payload_json)
    except Exception as e:
        raise ValueError(f"Invalid payload_json for task#{task.id}: {e}")

def _build_lines_for_send(task: Task, balances: dict) -> tuple[list[str], dict]:
    """
    根据订阅类型生成要发送的文本行，并返回预览信息（after/charge/type）
    """
    sub, cust = task.subscription, task.customer
    if not sub:
        raise ValueError("Task has no subscription")

    data = _payload(task)
    n = int(data.get("delivered_bottles", 0) or 0)
    if n <= 0:
        raise ValueError("delivered_bottles must > 0")

    if sub.type == "by_bottle":
        before = int(balances.get("bottle_balance") or 0)
        after = before - n
        lines = _render_template(task.template_key, {
            "customer_name": cust.name or cust.wx_display_name,
            "delivered_bottles": n,
            "balance_bottles_after": after,
            "remark": data.get("remark") or "",
        }).splitlines()
        preview = {"type": sub.type, "charge": n, "after": after}

    elif sub.type == "by_amount":
        unit = Decimal(str(sub.unit_price or "0"))
        charge = unit * n
        before_amt = Decimal(str(balances.get("amount_balance") or "0"))
        after_amt = before_amt - charge
        lines = _render_template(task.template_key, {
            "customer_name": cust.name or cust.wx_display_name,
            "delivered_bottles": n,
            "unit_price": f"{unit:.2f}",
            "amount_charge": f"{charge:.2f}",
            "balance_amount_after": f"{after_amt:.2f}",
            "used_amount": f"{Decimal('0.00'):.2f}",
            "total_amount": f"{before_amt:.2f}",
        }).splitlines()
        preview = {"type": sub.type, "charge": float(charge), "after": float(after_amt)}

    else:
        raise ValueError(f"Unknown subscription type: {sub.type}")

    # 简单长度/金额格式校验（可按需扩展）
    if len("\n".join(lines)) > 500:
        raise ValueError("message too long")

    return lines, preview

def _record_ledger_after_success(s, task: Task, preview: dict):
    sub, cust = task.subscription, task.customer
    if sub.type == "by_bottle":
        add_transaction(
            s,
            subscription_id=sub.id,
            customer_id=cust.id,
            kind="delivery",
            bottle_delta=-int(preview["charge"]),
            amount_delta=Decimal("0.00"),
            ref_task_id=task.id,
            memo="auto bottle delivery",
        )
    else:
        add_transaction(
            s,
            subscription_id=sub.id,
            customer_id=cust.id,
            kind="delivery",
            bottle_delta=0,
            amount_delta=-(Decimal(str(preview["charge"]))),
            ref_task_id=task.id,
            memo="auto amount delivery",
        )

def process_one_task(task_id: int):
    """
    调度器调用的唯一入口
    """
    from sender import send_text_lines  # 延迟导入，便于单元测试与可选依赖

    with session_scope() as s:
        task: Task | None = s.get(Task, task_id)
        if not task:
            logger.warning(f"Task#{task_id} not found.")
            return
        if task.status != "pending":
            logger.info(f"Task#{task_id} already processed: {task.status}")
            return

        try:
            # 取当前余额
            balances = recalc_subscription_balance(s, task.subscription_id)
            if not balances:
                raise ValueError("Subscription not found or no balance info")

            # 渲染文本，生成预览
            lines, preview = _build_lines_for_send(task, balances)
            logger.info(f"Preview Task#{task.id}: {preview}")

            # 真实发送（DRY_RUN=True 时仅模拟，不回车）
            contact = task.customer.wx_display_name or task.customer.name
            send_text_lines(contact, lines)

            # 发送成功后记账 + 更新任务状态
            _record_ledger_after_success(s, task, preview)
            mark_task_status(s, task, "sent", "ok", increment_try=True)
            logger.info(f"Task#{task.id} sent ok.")

        except Exception as e:
            logger.exception(e)
            mark_task_status(s, task, "failed", str(e), increment_try=True)
