# -*- coding: utf-8 -*-
# 仅在 DRY_RUN=True 下运行；会聚焦微信、打开搜索、粘贴两行（不回车）
from sender import send_text_lines
from config import DRY_RUN

print(f"DRY_RUN={DRY_RUN}")
if not DRY_RUN:
    print("⚠ Set DRY_RUN=True in config.py before this test.")
else:
    send_text_lines("文件传输助手", ["【自测】这是一条演练消息", "第二行：不会真的发送（不回车）"])
    print("✅ sender dry-run finished.")
