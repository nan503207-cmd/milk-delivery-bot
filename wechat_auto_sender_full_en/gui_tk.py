# -*- coding: utf-8 -*-
"""
中文界面 GUI（Tkinter）
标签页：客户与余额 / 任务队列
功能：查询客户、查看余额与流水、手动调整；查看/筛选/编辑/取消任务
"""

import json
from datetime import datetime
from decimal import Decimal

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

from config import DB_URL
from models import Base, Customer, Subscription, LedgerTransaction, Task
from db_utils import recalc_customer_balances, add_transaction

# ---------- 数据库初始化 ----------
engine = create_engine(DB_URL, future=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, future=True)


def fmt_dt(dt):
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return str(dt)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("自动发送控制台")
        self.geometry("980x680")

        nb = ttk.Notebook(self)
        self.tab_customer = ttk.Frame(nb)
        self.tab_tasks = ttk.Frame(nb)
        nb.add(self.tab_customer, text="客户与余额")
        nb.add(self.tab_tasks, text="任务队列")
        nb.pack(fill="both", expand=True)

        self._build_customer_tab()
        self._build_tasks_tab()

    # ---------------------- 客户与余额页 ----------------------
    def _build_customer_tab(self):
        frm = ttk.Frame(self.tab_customer, padding=12)
        frm.pack(fill="both", expand=True)

        # 顶部查询
        top = ttk.Frame(frm)
        top.pack(fill="x")
        ttk.Label(top, text="客户姓名或微信备注：").pack(side="left")
        self.entry_cust = ttk.Entry(top, width=28)
        self.entry_cust.pack(side="left", padx=6)
        ttk.Button(top, text="查询", command=self.on_search_customer).pack(side="left")

        body = ttk.Frame(frm)
        body.pack(fill="both", expand=True, pady=10)

        # 左侧：客户信息 + 余额表 + 手动调整
        left = ttk.Labelframe(body, text="客户信息与订阅余额", padding=10)
        left.pack(side="left", fill="y", padx=6)
        self.var_cust_info = tk.StringVar(value="未选择客户")
        ttk.Label(left, textvariable=self.var_cust_info, justify="left").pack(anchor="w")

        ttk.Label(left, text="订阅列表：").pack(anchor="w", pady=(8, 2))
        self.tree_bal = ttk.Treeview(
            left,
            columns=("sub_id", "type", "unit_price", "bottle", "amount"),
            show="headings",
            height=7,
        )
        # 表头（中文）
        self.tree_bal.heading("sub_id", text="订阅ID")
        self.tree_bal.heading("type", text="类型")
        self.tree_bal.heading("unit_price", text="单价")
        self.tree_bal.heading("bottle", text="瓶余额")
        self.tree_bal.heading("amount", text="金额余额")
        # 列宽
        self.tree_bal.column("sub_id", width=80, anchor="center")
        self.tree_bal.column("type", width=90, anchor="center")
        self.tree_bal.column("unit_price", width=90, anchor="e")
        self.tree_bal.column("bottle", width=90, anchor="e")
        self.tree_bal.column("amount", width=110, anchor="e")
        self.tree_bal.pack()

        adj = ttk.Labelframe(left, text="手动调整（正数为增加，负数为扣减）", padding=10)
        adj.pack(fill="x", pady=10)
        ttk.Label(adj, text="订阅ID：").grid(row=0, column=0, sticky="e")
        self.entry_adj_sub = ttk.Entry(adj, width=12)
        self.entry_adj_sub.grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(adj, text="瓶 Δ（整数）：").grid(row=1, column=0, sticky="e")
        self.entry_adj_bottle = ttk.Entry(adj, width=12)
        self.entry_adj_bottle.grid(row=1, column=1, sticky="w", padx=4)

        ttk.Label(adj, text="金额 Δ（¥）：").grid(row=2, column=0, sticky="e")
        self.entry_adj_amount = ttk.Entry(adj, width=12)
        self.entry_adj_amount.grid(row=2, column=1, sticky="w", padx=4)

        ttk.Label(adj, text="备注：").grid(row=3, column=0, sticky="e")
        self.entry_adj_memo = ttk.Entry(adj, width=28)
        self.entry_adj_memo.grid(row=3, column=1, sticky="w", padx=4)

        ttk.Button(adj, text="提交调整", command=self.on_adjust).grid(
            row=4, column=0, columnspan=2, pady=6
        )

        # 右侧：流水
        right = ttk.Labelframe(body, text="最近流水（最多 50 条）", padding=10)
        right.pack(side="left", fill="both", expand=True, padx=6)
        self.tree_tx = ttk.Treeview(
            right,
            columns=("id", "ts", "kind", "bottle", "amount", "memo", "sub_id"),
            show="headings",
        )
        self.tree_tx.heading("id", text="ID")
        self.tree_tx.heading("ts", text="时间")
        self.tree_tx.heading("kind", text="类型")
        self.tree_tx.heading("bottle", text="瓶差额")
        self.tree_tx.heading("amount", text="金额差额")
        self.tree_tx.heading("memo", text="备注")
        self.tree_tx.heading("sub_id", text="订阅ID")

        self.tree_tx.column("id", width=60, anchor="center")
        self.tree_tx.column("ts", width=150, anchor="center")
        self.tree_tx.column("kind", width=100, anchor="center")
        self.tree_tx.column("bottle", width=90, anchor="e")
        self.tree_tx.column("amount", width=110, anchor="e")
        self.tree_tx.column("memo", width=320, anchor="w")
        self.tree_tx.column("sub_id", width=90, anchor="center")
        self.tree_tx.pack(fill="both", expand=True)

        self._current_customer = None

    def on_search_customer(self):
        name = self.entry_cust.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入客户姓名或微信备注再查询。")
            return
        with Session() as s:
            cust = (
                s.query(Customer)
                .filter((Customer.name == name) | (Customer.wx_display_name == name))
                .first()
            )
            if not cust:
                messagebox.showinfo("结果", "未找到该客户。")
                return
            self._current_customer = cust
            self.var_cust_info.set(
                f"客户ID：{cust.id}\n姓名：{cust.name or ''}\n微信备注：{cust.wx_display_name or ''}"
            )
            # 刷新余额表
            for i in self.tree_bal.get_children():
                self.tree_bal.delete(i)
            for b in recalc_customer_balances(s, cust.id):
                self.tree_bal.insert(
                    "",
                    "end",
                    values=(
                        b["subscription_id"],
                        "按瓶" if b["type"] == "by_bottle" else "按金额",
                        b.get("unit_price") if b["type"] == "by_amount" else "",
                        b.get("bottle_balance") if b["type"] == "by_bottle" else "",
                        b.get("amount_balance") if b["type"] == "by_amount" else "",
                    ),
                )
            # 刷新流水
            for i in self.tree_tx.get_children():
                self.tree_tx.delete(i)
            q = (
                s.query(LedgerTransaction)
                .filter(LedgerTransaction.customer_id == cust.id)
                .order_by(desc(LedgerTransaction.ts))
                .limit(50)
            )
            for t in q:
                self.tree_tx.insert(
                    "",
                    "end",
                    values=(
                        t.id,
                        fmt_dt(t.ts),
                        t.kind,
                        t.bottle_delta,
                        str(t.amount_delta),
                        t.memo or "",
                        t.subscription_id,
                    ),
                )

    def on_adjust(self):
        if not self._current_customer:
            messagebox.showwarning("提示", "请先查询并选择客户。")
            return
        sub_id = self.entry_adj_sub.get().strip()
        if not sub_id.isdigit():
            messagebox.showwarning("提示", "订阅ID必须为数字。")
            return
        bottle = self.entry_adj_bottle.get().strip()
        amount = self.entry_adj_amount.get().strip()
        memo = self.entry_adj_memo.get().strip()

        try:
            bottle_delta = int(bottle) if bottle else 0
        except Exception:
            messagebox.showwarning("提示", "瓶 Δ 必须为整数。")
            return
        try:
            amount_delta = Decimal(amount) if amount else Decimal("0.00")
        except Exception:
            messagebox.showwarning("提示", "金额 Δ 必须为数字。")
            return

        with Session() as s:
            sub = s.query(Subscription).get(int(sub_id))
            if not sub or sub.customer_id != self._current_customer.id:
                messagebox.showerror("错误", "未找到该订阅，或订阅不属于当前客户。")
                return
            add_transaction(
                s,
                subscription_id=sub.id,
                customer_id=self._current_customer.id,
                kind="manual_adjust",
                bottle_delta=bottle_delta,
                amount_delta=amount_delta,
                memo=memo,
            )
            s.commit()
        messagebox.showinfo("成功", "已保存调整。")
        self.on_search_customer()

    # ---------------------- 任务队列页 ----------------------
    def _build_tasks_tab(self):
        frm = ttk.Frame(self.tab_tasks, padding=12)
        frm.pack(fill="both", expand=True)

        # 过滤区
        filt = ttk.Frame(frm)
        filt.pack(fill="x")
        ttk.Label(filt, text="状态：").pack(side="left")
        self.combo_status = ttk.Combobox(
            filt, values=["pending", "sent", "failed", "canceled"], width=10
        )
        self.combo_status.set("pending")
        self.combo_status.pack(side="left", padx=4)
        ttk.Label(filt, text="客户：").pack(side="left")
        self.entry_task_cust = ttk.Entry(filt, width=20)
        self.entry_task_cust.pack(side="left", padx=4)
        ttk.Button(filt, text="查询", command=self.on_query_tasks).pack(side="left", padx=4)

        # 任务表
        self.tree_tasks = ttk.Treeview(
            frm,
            columns=("id", "cust_id", "sub_id", "send_time", "tmpl", "status"),
            show="headings",
        )
        self.tree_tasks.heading("id", text="任务ID")
        self.tree_tasks.heading("cust_id", text="客户ID")
        self.tree_tasks.heading("sub_id", text="订阅ID")
        self.tree_tasks.heading("send_time", text="发送时间")
        self.tree_tasks.heading("tmpl", text="模板键")
        self.tree_tasks.heading("status", text="状态")

        self.tree_tasks.column("id", width=80, anchor="center")
        self.tree_tasks.column("cust_id", width=90, anchor="center")
        self.tree_tasks.column("sub_id", width=90, anchor="center")
        self.tree_tasks.column("send_time", width=180, anchor="center")
        self.tree_tasks.column("tmpl", width=200, anchor="w")
        self.tree_tasks.column("status", width=100, anchor="center")
        self.tree_tasks.pack(fill="both", expand=True, pady=8)

        actions = ttk.Frame(frm)
        actions.pack(fill="x")
        ttk.Button(actions, text="编辑任务", command=self.on_edit_task).pack(side="left")
        ttk.Button(actions, text="取消任务", command=self.on_cancel_task).pack(
            side="left", padx=8
        )

    def on_query_tasks(self):
        status = self.combo_status.get()
        name = self.entry_task_cust.get().strip()
        with Session() as s:
            q = s.query(Task)
            if status:
                q = q.filter(Task.status == status)
            if name:
                cust = (
                    s.query(Customer)
                    .filter((Customer.name == name) | (Customer.wx_display_name == name))
                    .first()
                )
                if cust:
                    q = q.filter(Task.customer_id == cust.id)
                else:
                    self._fill_tasks([])
                    messagebox.showinfo("结果", "未找到该客户。")
                    return
            tasks = q.order_by(Task.send_time.asc()).limit(300).all()
            self._fill_tasks(tasks)

    def _fill_tasks(self, tasks):
        for i in self.tree_tasks.get_children():
            self.tree_tasks.delete(i)
        for t in tasks:
            self.tree_tasks.insert(
                "",
                "end",
                values=(
                    t.id,
                    t.customer_id,
                    t.subscription_id,
                    fmt_dt(t.send_time),
                    t.template_key,
                    t.status,
                ),
            )

    def _get_selected_task_id(self):
        sel = self.tree_tasks.selection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一条任务。")
            return None
        return int(self.tree_tasks.item(sel[0], "values")[0])

    def on_cancel_task(self):
        tid = self._get_selected_task_id()
        if not tid:
            return
        if not messagebox.askyesno("确认", f"确定取消任务 #{tid} 吗？"):
            return
        with Session() as s:
            t = s.query(Task).get(tid)
            if not t:
                messagebox.showerror("错误", "未找到该任务。")
                return
            t.status = "canceled"
            t.updated_at = datetime.now()
            s.add(t)
            s.commit()
        messagebox.showinfo("成功", "已取消任务。")
        self.on_query_tasks()

    def on_edit_task(self):
        tid = self._get_selected_task_id()
        if not tid:
            return
        EditTaskDialog(self, tid)


# ---------------------- 编辑任务弹窗 ----------------------
class EditTaskDialog(tk.Toplevel):
    def __init__(self, master, task_id: int):
        super().__init__(master)
        self.title(f"编辑任务 #{task_id}")
        self.geometry("640x500")
        self.task_id = task_id
        self._load_task()

    def _load_task(self):
        with Session() as s:
            self.task = s.query(Task).get(self.task_id)
            if not self.task:
                messagebox.showerror("错误", "未找到该任务。")
                self.destroy()
                return

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)
        ttk.Label(
            frm,
            text=f"任务ID：{self.task.id}    客户ID：{self.task.customer_id}    订阅ID：{self.task.subscription_id}",
        ).pack(anchor="w")

        row1 = ttk.Frame(frm)
        row1.pack(fill="x", pady=6)
        ttk.Label(row1, text="发送时间（YYYY-MM-DD HH:MM:SS）：").pack(side="left")
        self.entry_time = ttk.Entry(row1, width=24)
        self.entry_time.insert(0, fmt_dt(self.task.send_time))
        self.entry_time.pack(side="left", padx=4)

        row2 = ttk.Frame(frm)
        row2.pack(fill="x", pady=6)
        ttk.Label(row2, text="模板键：").pack(side="left")
        self.entry_tmpl = ttk.Entry(row2, width=30)
        self.entry_tmpl.insert(0, self.task.template_key or "")
        self.entry_tmpl.pack(side="left", padx=4)

        ttk.Label(frm, text="Payload JSON：").pack(anchor="w")
        self.txt_payload = scrolledtext.ScrolledText(frm, height=12)
        self.txt_payload.pack(fill="both", expand=True)
        self.txt_payload.insert("1.0", self.task.payload_json or "")

        btns = ttk.Frame(frm)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="保存", command=self.on_save).pack(side="left")
        ttk.Button(btns, text="关闭", command=self.destroy).pack(side="right")

    def on_save(self):
        t = self.entry_time.get().strip()
        k = self.entry_tmpl.get().strip()
        p = self.txt_payload.get("1.0", "end").strip()
        try:
            dt = datetime.fromisoformat(t)
        except Exception:
            messagebox.showerror("错误", "时间格式应为：YYYY-MM-DD HH:MM:SS")
            return
        if p:
            try:
                json.loads(p)
            except Exception as e:
                messagebox.showerror("错误", f"Payload 必须为合法 JSON：{e}")
                return
        with Session() as s:
            task = s.query(Task).get(self.task_id)
            if not task:
                messagebox.showerror("错误", "未找到该任务。")
                return
            task.send_time = dt
            task.template_key = k or task.template_key
            task.payload_json = p or None
            task.updated_at = datetime.now()
            s.add(task)
            s.commit()
        messagebox.showinfo("成功", "已保存修改。")
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
