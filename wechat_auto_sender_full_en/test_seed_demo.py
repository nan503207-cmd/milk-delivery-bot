# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DB_URL
from models import Base, Customer, Subscription, Task
from db_utils import add_transaction

engine = create_engine(DB_URL, future=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, future=True)

with Session() as s:
    # 清理历史演示数据（可选）
    s.query(Task).delete()
    s.query(Subscription).delete()
    s.query(Customer).delete()
    s.commit()

    zhang = Customer(wx_display_name="张三", name="张三")
    li = Customer(wx_display_name="李四", name="李四")
    s.add_all([zhang, li]); s.flush()

    sub_bottle = Subscription(customer_id=zhang.id, type="by_bottle", status="active")
    sub_amount = Subscription(customer_id=li.id, type="by_amount", unit_price=Decimal("5.50"), status="active")
    s.add_all([sub_bottle, sub_amount]); s.flush()

    # 初始化余额：张三 +30 瓶；李四 +100 元
    add_transaction(s, sub_bottle.id, zhang.id, kind="purchase", bottle_delta=30, amount_delta=Decimal("0.00"), memo="seed bottles")
    add_transaction(s, sub_amount.id, li.id, kind="purchase", bottle_delta=0, amount_delta=Decimal("100.00"), memo="seed amount")

    # 加两条任务（即将到时）
    now = datetime.now()
    t1 = Task(customer_id=zhang.id, subscription_id=sub_bottle.id, send_time=now + timedelta(seconds=10),
              template_key="confirm_by_bottle", payload_json='{"delivered_bottles": 2, "remark":"测试"}')
    t2 = Task(customer_id=li.id, subscription_id=sub_amount.id, send_time=now + timedelta(seconds=15),
              template_key="confirm_by_amount", payload_json='{"delivered_bottles": 3}')
    s.add_all([t1, t2]); s.commit()

print("✅ Seeded demo customers/subscriptions/tasks.")
