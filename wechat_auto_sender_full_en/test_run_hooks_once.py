# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import DB_URL
from models import Base, Task
from hooks import process_one_task

engine = create_engine(DB_URL, future=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, future=True)

with Session() as s:
    task = s.query(Task).filter(Task.status=="pending", Task.send_time <= datetime.now()).order_by(Task.send_time.asc()).first()
    if not task:
        print("⚠ 没有到期的 pending 任务。可等待几秒后再试，或把一条任务的 send_time 改成当前时间之前。")
    else:
        print(f"处理任务 task#{task.id} ...")
        process_one_task(task.id)
        s.expire_all()
        task2 = s.query(Task).get(task.id)
        print(f"结果：task#{task2.id} status={task2.status}, try_count={task2.try_count}, result_log={task2.result_log}")
print("✅ hooks one-shot finished.")
