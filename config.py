#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置文件
包含应用程序的所有配置参数
"""

# ***********************************************************************
# Modified based on the My-Dream-Moments project
# Copyright of the original project: Copyright (C) 2025, umaru
# Copyright of this modification: Copyright (C) 2025, iwyxdxl
# Licensed under GNU GPL-3.0 or higher, see the LICENSE file for details.
# ***********************************************************************

# 用户列表(请配置要和bot说话的账号的微信昵称，不要写备注！)
# 例如：LISTEN_LIST = ['用户1','用户2']
LISTEN_LIST = ['文件传输助手','梁培利','螃蟹青年']
GROUP_LIST = ['测试2','AI 产品经理小组']
BOT_NAME = '螃蟹青年星'

# DeepSeek API 配置
DEEPSEEK_API_KEY = 'sk-ptlmtumpudtgxkiufynwnmsrccpvwaywhtkpvspqsnybdsmz'
# 硅基流动API注册地址，免费15元额度 https://cloud.siliconflow.cn/
DEEPSEEK_BASE_URL = 'https://api.siliconflow.cn/v1/'
# 硅基流动API的模型
MODEL = 'Pro/deepseek-ai/DeepSeek-V3'

#火山方舟配置
ARK_API_KEY = '7b233883-61dd-4087-8dec-12c0ca0b70eb'
ARK_BASE_URL = 'https://ark.cn-beijing.volces.com/api/v3'
ARK_MODEL = 'bot-20250219111142-fql46'
USE_ARK_API = True

# 如果要使用官方的API
# DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
# 官方API的V3模型
# MODEL = 'deepseek-chat'

#COZE配置
#测试API
#COZE_API_KEY = 'pat_L1RHaMzCeeOeEcJmePAqEUWGrMJSEJLsrFQNXIXgCGWUkuzUYpF8c9cUPV76CgaT'

COZE_API_KEY = 'pat_lxKXyKdrF0IRFPM0NqMPXaBBATs8U3rI9vNUN4XSsZYo6vFp5PJYzopaXYY6ydR6'
#测试ID
#COZE_BOT_ID = '7481688080375169087'
COZE_BOT_ID = '7480740807264239631'
COZE_API_ENDPOINT = 'https://api.coze.cn/v3/chat'
COZE_TRIGGER_KEYWORDS = ['星座']
COZE_DATABASE_KEYWORDS = ['金币余额','签到']

# 回复最大token
MAX_TOKEN = 2000
# DeepSeek温度
TEMPERATURE = 1.1
# Moonshot AI配置（用于图片和表情包识别）
# API申请https://platform.moonshot.cn/
MOONSHOT_API_KEY = 'sk-0RuxglJsBJxsDzzHSqT9IF3vBARtCYKU4TgTEYIjdJf3h6hP'
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"
MOONSHOT_MODEL = "moonshot-v1-128k-vision-preview"
MOONSHOT_TEMPERATURE = 0.3
#表情包存放目录
EMOJI_DIR = 'emojis'
# 自动消息配置
AUTO_MESSAGE = "请你模拟系统设置的角色，在微信上找对方发消息想知道对方在做什么"
MIN_COUNTDOWN_HOURS = 0.2  # 最小倒计时时间（小时）
MAX_COUNTDOWN_HOURS = 0.5  # 最大倒计时时间（小时）
# 消息发送时间限制
QUIET_TIME_START = "22:00"  # 安静时间开始
QUIET_TIME_END = "8:00"    # 安静时间结束 