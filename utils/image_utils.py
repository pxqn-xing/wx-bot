#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
图像处理工具
"""

import os
import time
import pyautogui
from datetime import datetime
from wxauto import WeChat
import logging

logger = logging.getLogger(__name__)

def capture_and_save_screenshot(who, root_dir):
    """
    截取微信聊天窗口的截图并保存
    
    Args:
        who (str): 聊天对象名称
        root_dir (str): 项目根目录
        
    Returns:
        str: 保存的截图路径
    """
    screenshot_folder = os.path.join(root_dir, 'screenshot')
    if not os.path.exists(screenshot_folder):
        os.makedirs(screenshot_folder)
    
    screenshot_path = os.path.join(
        screenshot_folder, 
        f'{who}_{datetime.now().strftime("%Y%m%d%H%M%S")}.png'
    )

    try:
        # 激活并定位微信聊天窗口
        wx_chat = WeChat()
        wx_chat.ChatWith(who)
        chat_window = pyautogui.getWindowsWithTitle(who)[0]

        # 确保窗口被前置和激活
        if not chat_window.isActive:
            chat_window.activate()
        if not chat_window.isMaximized:
            chat_window.maximize()

        # 获取窗口的坐标和大小
        x, y, width, height = chat_window.left, chat_window.top, chat_window.width, chat_window.height

        # 等待窗口完全加载
        time.sleep(1)

        # 截取指定窗口区域的屏幕
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        screenshot.save(screenshot_path)
        logger.info(f'已保存截图: {screenshot_path}')
        return screenshot_path
    except Exception as e:
        logger.error(f'保存截图失败: {str(e)}')
        return None 