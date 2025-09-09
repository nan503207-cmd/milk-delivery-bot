# -*- coding: utf-8 -*-
from contextlib import contextmanager
from decimal import Decimal
from datetime import datetime

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from config import DB_URL
from models import Base, Customer, Subscription, LedgerTransaction, Task

_engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
_SessionLocal = sessionmaker(bind=_engine, future=True)

def init_db():
    Base.metadata.create_all(_engine)

@contextmanager
def session_scope():
    s = _SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()

def fetch_due_tasks(s, now=None, limit=50):
    now = now or datetime.now()
    return (
        s.query(Task)
        .filter(Task.status == "pending", Task.send_time <= now)
        .order_by(Task.send_time.asc())
        .limit(limit)
        .all()
    )

def mark_task_status(s, task: Task, status: str, result_log: str = None, increment_try=True):
    task.status = status
    if result_log is not None:
        task.result_log = (result_log or "")[:1000]
    if increment_try:
        task.try_count = (task.try_count or 0) + 1
    task.updated_at = datetime.now()
    s.add(task)

def add_transaction(
    s,
    subscription_id: int,
    customer_id: int,
    kind: str,
    bottle_delta: int = 0,
    amount_delta: Decimal = Decimal("0.00"),
    ref_task_id: int = None,
    memo: str = None,
):
    """新增一条台账流水（正数=入账，负数=扣减）"""
    t = LedgerTransaction(
        subscription_id=subscription_id,
        customer_id=customer_id,
        kind=kind,
        bottle_delta=bottle_delta,
        amount_delta=amount_delta,
        ref_task_id=ref_task_id,
        memo=memo,
    )
    s.add(t)
    return t

def recalc_subscription_balance(s, subscription_id: int):
    sub = s.query(Subscription).get(subscription_id)
    if not sub:
        return None
    bottle_sum = (
        s.query(func.coalesce(func.sum(LedgerTransaction.bottle_delta), 0))
        .filter(LedgerTransaction.subscription_id == subscription_id)
        .scalar()
    )
    amount_sum = (
        s.query(func.coalesce(func.sum(LedgerTransaction.amount_delta), 0))
        .filter(LedgerTransaction.subscription_id == subscription_id)
        .scalar()
    )
    return {
        "subscription_id": subscription_id,
        "type": sub.type,
        "unit_price": float(sub.unit_price) if sub.unit_price is not None else None,
        "bottle_balance": int(bottle_sum or 0),
        "amount_balance": float(amount_sum or 0.0),
    }

def recalc_customer_balances(s, customer_id: int):
    subs = s.query(Subscription).filter(Subscription.customer_id == customer_id).all()
    return [recalc_subscription_balance(s, x.id) for x in subs]
