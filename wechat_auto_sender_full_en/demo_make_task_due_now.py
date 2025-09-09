# -*- coding: utf-8 -*-
"""
创建一个“马上到点”的任务，目标联系人=文件传输助手
- 新建客户(微信备注=文件传输助手) + 订阅 + 初始余额
- 生成一条 10 秒后到点的任务（模板：confirm_by_bottle，实送2瓶）
"""

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
    # 若已存在“文件传输助手”客户，就复用
    cust = s.query(Customer).filter(Customer.wx_display_name=="文件传输助手").first()
    if not cust:
        cust = Customer(wx_display_name="文件传输助手", name="文件传输助手")
        s.add(cust); s.flush()

    # 给他建一个“按瓶”订阅并充值 10 瓶（若已有同类订阅则复用）
    sub = s.query(Subscription).filter(Subscription.customer_id==cust.id, Subscription.type=="by_bottle").first()
    if not sub:
        sub = Subscription(customer_id=cust.id, type="by_bottle", status="active")
        s.add(sub); s.flush()
        add_transaction(s, subscription_id=sub.id, customer_id=cust.id,
                        kind="purchase", bottle_delta=10, amount_delta=Decimal("0.00"), memo="demo init 10 bottles")

    # 10 秒后到点的任务
    now = datetime.now()
    task = Task(customer_id=cust.id, subscription_id=sub.id,
                send_time=now + timedelta(seconds=2),
                template_key="confirm_by_bottle",
                payload_json='{"delivered_bottles": 2, "remark": "【演练】不回车，仅粘贴"}')
    s.add(task); s.commit()
    print(f"✅ 已创建演示任务：task#{task.id}，10 秒后到点。")
    print("   下一步：运行 Start_Scheduler.bat（或看下方脚本二的“立即执行”）。")
