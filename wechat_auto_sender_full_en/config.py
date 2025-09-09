# -*- coding: utf-8 -*-
"""
配置文件 config.py
你可以在这里调整数据库、运行模式、日志、调度参数等。
"""

# SQLite 数据库文件
DB_URL = "sqlite:///wechat_tasks.db"

# 是否只模拟发送（True=仅打印日志，不实际操作微信）
DRY_RUN = True

# 时区
TIMEZONE = "Asia/Shanghai"

# 截图/审计日志目录
AUDIT_DIR = "audit"

# 模板目录
TEMPLATE_DIR = "templates"

# 日志文件路径
LOG_PATH = "wechat_run.log"

# 调度器每次扫描任务的间隔（秒）
SCAN_INTERVAL_SECONDS = 20

# 两条消息之间的最小安全间隔（秒）
GLOBAL_MIN_INTERVAL = 3.5

# 单条消息内部打字/点击的安全延迟（秒范围，可加抖动）
SAFE_GAP_PER_MSG = 3.5
JITTER_SECONDS = (0.8, 2.2)  # 随机扰动，防止太机械

# 每条任务最大重试次数
MAX_RETRY = 3

# 夜间静默模式（避免深夜打扰）
NIGHT_SILENT = False
NIGHT_START = 22   # 晚上 22 点后不发
NIGHT_END = 7      # 早上 7 点前不发
