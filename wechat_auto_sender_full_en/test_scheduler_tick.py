# -*- coding: utf-8 -*-
# 手动调用 scheduler.worker() 扫描并处理到期任务一次（不启动定时循环）
import scheduler
scheduler.worker()
print("✅ scheduler tick finished.")
