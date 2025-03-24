#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
时间相关工具函数
"""

import logging
from datetime import datetime
from config import QUIET_TIME_START, QUIET_TIME_END

def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def parse_time(time_str):
    """将时间字符串解析为时间对象"""
    return datetime.strptime(time_str, "%H:%M").time()

def is_quiet_time():
    """
    判断当前是否为安静时间段
    安静时间段内不发送自动消息
    """
    current_time = datetime.now().time()
    quiet_time_start = parse_time(QUIET_TIME_START)
    quiet_time_end = parse_time(QUIET_TIME_END)
    
    if quiet_time_start <= quiet_time_end:
        return quiet_time_start <= current_time <= quiet_time_end
    else:
        return current_time >= quiet_time_start or current_time <= quiet_time_end

def get_formatted_time():
    """获取格式化的当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S") 