# -*- coding: utf-8 -*-
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from config import DB_URL
from models import Base, Customer, Subscription, LedgerTransaction, Task

engine = create_engine(DB_URL, future=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, future=True)

with Session() as s:
    print("=== Customers ===")
    for c in s.query(Customer).all():
        print(f"- #{c.id} {c.name or ''} / {c.wx_display_name}")

    print("\n=== Subscriptions ===")
    for sub in s.query(Subscription).all():
        bottle = s.query(func.coalesce(func.sum(LedgerTransaction.bottle_delta), 0)).filter(
            LedgerTransaction.subscription_id == sub.id).scalar()
        amount = s.query(func.coalesce(func.sum(LedgerTransaction.amount_delta), 0)).filter(
            LedgerTransaction.subscription_id == sub.id).scalar()
        print(f"- sub#{sub.id} type={sub.type} unit={sub.unit_price} bottle_balance={bottle} amount_balance={amount}")

    print("\n=== Tasks ===")
    for t in s.query(Task).order_by(Task.send_time.asc()).all():
        print(f"- task#{t.id} cust={t.customer_id} sub={t.subscription_id} time={t.send_time} key={t.template_key} status={t.status}")
print("✅ Printed state.")
