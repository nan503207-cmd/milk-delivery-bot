# -*- coding: utf-8 -*-
"""
sender.py
封装实际“把文本发到微信”的动作。
DRY_RUN=True 时只粘贴不回车，便于安全演练。
"""

import time
import random
from datetime import datetime

import pyautogui as gui
import pyperclip

try:
    from loguru import logger
except Exception:  # pragma: no cover
    class _L:
        def info(self, *a, **k): print("[INFO]", *a)
        def warning(self, *a, **k): print("[WARN]", *a)
        def error(self, *a, **k): print("[ERROR]", *a)
        def exception(self, *a, **k): print("[EXC]", *a)
    logger = _L()

# 可从 config 读取的选项（给默认值，兼容你的极简 config.py）
try:
    from config import DRY_RUN, AUDIT_DIR, SAFE_GAP_PER_MSG, JITTER_SECONDS
except Exception:
    DRY_RUN = True
    AUDIT_DIR = "audit"
    SAFE_GAP_PER_MSG = 3.5
    JITTER_SECONDS = (0.8, 2.2)

def _jitter(a=0.8, b=2.2):
    time.sleep(random.uniform(a, b))

def _human_pause(sec: float):
    time.sleep(sec + random.uniform(0, 0.6))

def _focus_wechat():
    """
    激活微信窗口，排除浏览器里的“微信”标签。
    """
    try:
        import pygetwindow as gw
        candidates = gw.getWindowsWithTitle("微信") + gw.getWindowsWithTitle("WeChat")
        # 过滤掉浏览器窗口
        filtered = [w for w in candidates if not any(b in w.title for b in ["Chrome", "Edge", "Firefox", "Safari"])]
        if filtered:
            wx = filtered[0]
            try:
                wx.restore()
                wx.activate()
            except Exception:
                wx.minimize()
                wx.restore()
            time.sleep(0.5)
            logger.info(f"已切换到微信窗口: {wx.title}")
            return True
        else:
            logger.error("未找到合适的微信窗口，请确认已打开微信客户端")
            return False
    except Exception as e:
        logger.error(f"激活微信窗口失败: {e}")
        return False

def _open_search():
    gui.hotkey("ctrl", "f")  # 微信搜索
    _jitter(*JITTER_SECONDS)

def _paste_text(t: str):
    pyperclip.copy(t)
    _jitter(0.2, 0.5)
    gui.hotkey("ctrl", "v")

def _find_and_open_contact(name: str):
    _open_search()
    _paste_text(name)
    _jitter(0.5, 0.8)   # 等待搜索结果刷新
    gui.press("enter")
    # _jitter(0.3, 0.5)   # 给微信反应时间
    # gui.press("enter")  # 再按一次，确保进入聊天
    _human_pause(0.6)
    # 👇 点击输入框位置（x,y需要你自己量一下）
    gui.click(1275, 850)   # 假设输入框大概在屏幕底部
    _human_pause(0.3)

def send_text_lines(contact_name: str, lines: list[str]):
    """
    把多行文本发送给联系人（或单聊窗口）。
    DRY_RUN=True: 只粘贴不回车；False: 每行回车发送。
    """
    logger.info(f"Sending to '{contact_name}' ({len(lines)} lines), DRY_RUN={DRY_RUN}")

    _focus_wechat()
    _find_and_open_contact(contact_name)

    for line in lines:
        if not line.strip():
            continue
        _paste_text(line)
        _jitter(0.4, 0.9)

        # 可选截图留存
        try:
            from config import SCREENSHOT_ON_SEND
            if SCREENSHOT_ON_SEND:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                gui.screenshot(f"{AUDIT_DIR}/send_{ts}.png")
        except Exception:
            pass

        if not DRY_RUN:
            gui.press("enter")
        _human_pause(float(SAFE_GAP_PER_MSG))

import pygetwindow as gw
windows = gw.getWindowsWithTitle("微信")
if windows:
    wx = windows[0]
    wx.activate()
    wx.maximize()
    time.sleep(0.5)