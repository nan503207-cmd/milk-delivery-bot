# -*- coding: utf-8 -*-
"""
Scheduler — 读取 config.py 的参数进行轮询调度
优先调用 hooks.process_one_task(task_id) 真正执行任务；
若没有 hooks.py，则做占位处理（把任务标记为 sent，便于先跑通）。
"""

from datetime import datetime
import time

try:
    # 可选：更好看的日志
    from loguru import logger
except Exception:
    import logging as logger
    logger.basicConfig(level=20)

from apscheduler.schedulers.background import BackgroundScheduler

from config import (
    TIMEZONE,
    SCAN_INTERVAL_SECONDS,
    GLOBAL_MIN_INTERVAL,
    NIGHT_SILENT,
    NIGHT_START,
    NIGHT_END,
)
from db_utils import session_scope, fetch_due_tasks, mark_task_status


# --- 可选动作：若存在 hooks.py，则使用里面的真正处理函数 ---
_PROCESSOR = None
try:
    from hooks import process_one_task as _PROCESSOR  # type: ignore
    logger.info("Scheduler: using hooks.process_one_task()")
except Exception:
    logger.warning(
        "Scheduler: hooks.process_one_task 未找到，将使用占位处理（仅标记 sent）。"
    )


def _night_silent_now(now: datetime) -> bool:
    """根据配置判断当前是否处于夜间静默时段"""
    if not NIGHT_SILENT:
        return False
    h = now.hour
    # 兼容跨零点区间（例如 22:00 ~ 07:00）
    if NIGHT_START <= NIGHT_END:
        return NIGHT_START <= h < NIGHT_END
    else:
        return h >= NIGHT_START or h < NIGHT_END


def _placeholder_handle(task, s):
    """没有 hooks 时的占位处理：仅把任务标记为 sent"""
    mark_task_status(s, task, "sent", result_log="placeholder sent", increment_try=True)
    logger.info(f"[PLACEHOLDER] Marked task #{task.id} as sent.")


def worker():
    """定时扫描并处理到期任务"""
    now = datetime.now()
    if _night_silent_now(now):
        logger.info("Night-silent window. Skip this tick.")
        return

    with session_scope() as s:
        due = fetch_due_tasks(s, now=now, limit=20)
        if not due:
            return

        logger.info(f"Found {len(due)} due tasks.")
        for t in due:
            try:
                if _PROCESSOR:
                    # 真正处理（会做模板渲染、余额校验、发送/记账等）
                    _PROCESSOR(t.id)
                else:
                    # 占位处理
                    _placeholder_handle(t, s)
            except Exception as e:
                logger.exception(e)
            finally:
                # 为了更“像人”，每条任务留出全局最小间隔
                time.sleep(float(GLOBAL_MIN_INTERVAL))


def start_scheduler():
    logger.info(
        f"Scheduler starting... tz={TIMEZONE}, interval={SCAN_INTERVAL_SECONDS}s, "
        f"night_silent={'ON' if NIGHT_SILENT else 'OFF'}"
    )
    sched = BackgroundScheduler(timezone=TIMEZONE)
    # 串行执行；coalesce 合并漏掉的 tick；interval 从 config 读取
    sched.add_job(
        worker,
        "interval",
        seconds=int(SCAN_INTERVAL_SECONDS),
        id="wechat_worker",
        max_instances=1,
        coalesce=True,
    )
    sched.start()
    logger.info("Scheduler started.")
    return sched
