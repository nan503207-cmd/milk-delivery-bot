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

s = Session()

# 创建客户
zhangsan = Customer(wx_display_name="张三", name="张三")
lisi = Customer(wx_display_name="李四", name="李四")
s.add_all([zhangsan, lisi]); s.commit()

# 创建套餐：张三按瓶、李四按金额
sub1 = Subscription(customer_id=zhangsan.id, type='by_bottle', unit_price=None, status='active')
sub2 = Subscription(customer_id=lisi.id, type='by_amount', unit_price=Decimal('5.50'), status='active')
s.add_all([sub1, sub2]); s.commit()

# 充值/进账
add_transaction(s, subscription_id=sub1.id, customer_id=zhangsan.id,
                kind='purchase', bottle_delta=30, amount_delta=0, memo='首购30瓶')
add_transaction(s, subscription_id=sub2.id, customer_id=lisi.id,
                kind='purchase', bottle_delta=0, amount_delta=Decimal('100.00'), memo='充值¥100')
s.commit()

# 生成两条即将到时的发送任务
now = datetime.now()
t1 = Task(customer_id=zhangsan.id, subscription_id=sub1.id,
          send_time=now + timedelta(seconds=15),
          template_key='confirm_by_bottle',
          payload_json='{"delivered_bottles": 2, "remark": "早上到家～"}')
t2 = Task(customer_id=lisi.id, subscription_id=sub2.id,
          send_time=now + timedelta(seconds=25),
          template_key='confirm_by_amount',
          payload_json='{"delivered_bottles": 3}')
s.add_all([t1, t2]); s.commit()

print("Seeded demo data. Now run: python main.py (or Start_Scheduler.bat)")
s.close()
