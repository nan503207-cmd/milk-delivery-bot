# -*- coding: utf-8 -*-
"""
找一条“已到点”的 pending 任务，直接调用 hooks 立即执行一次
（DRY_RUN=True 时只粘贴不回车；False 时会真的发送）
"""
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DB_URL
from models import Base, Task
from hook import process_one_task

engine = create_engine(DB_URL, future=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, future=True)

with Session() as s:
    t = (s.query(Task)
           .filter(Task.status=="pending", Task.send_time<=datetime.now())
           .order_by(Task.send_time.asc())
           .first())
    if not t:
        print("⚠ 没有已到点的 pending 任务。先跑 demo_make_task_due_now.py，或把某条任务的时间改早一点。")
    else:
        print(f"执行 task#{t.id} ...")
        process_one_task(t.id)
        s.expire_all()
        t2 = s.query(Task).get(t.id)
        print(f"结果：status={t2.status}, try_count={t2.try_count}, result_log={t2.result_log}")
