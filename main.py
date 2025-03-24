#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主程序入口
"""

import logging
import threading
import time
import shutil
import os

from wechat.listener import WeChatListener
from wechat.sender import WeChatSender
from user.manager import UserManager
from utils.time_utils import setup_logging
from database import init_db

# 设置日志
logger = setup_logging()

def clean_up_temp_files():
    """清理临时文件和目录"""
    temp_dirs = ["screenshot", "wxauto文件"]
    for dir_name in temp_dirs:
        if os.path.isdir(dir_name):
            shutil.rmtree(dir_name)
            logger.info(f"目录 {dir_name} 已成功删除")
        else:
            logger.info(f"目录 {dir_name} 不存在，无需删除")

def main():
    """主函数"""
    try:
        # 初始化数据库
        init_db()
        
        # 清理临时文件
        clean_up_temp_files()
        
        # 初始化微信发送器
        sender = WeChatSender()
        
        # 初始化用户管理器
        user_manager = UserManager(sender)
        
        # 初始化微信监听器
        listener = WeChatListener(user_manager)
        
        # 启动消息监听线程
        listener_thread = threading.Thread(target=listener.start)
        listener_thread.daemon = True
        listener_thread.start()
        
        # 启动用户消息处理线程
        checker_thread = threading.Thread(target=user_manager.check_inactive_users)
        checker_thread.daemon = True
        checker_thread.start()
        
        # 启动用户超时检查线程
        #timeout_thread = threading.Thread(target=user_manager.check_user_timeouts)
        #timeout_thread.daemon = True
        #timeout_thread.start()
        
        logger.info("机器人已启动，等待消息...")
        
        # 主循环保持程序运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("用户终止程序")
    except Exception as e:
        logger.error(f"程序运行异常: {str(e)}", exc_info=True)
    finally:
        logger.info("程序退出")

if __name__ == "__main__":
    main() 