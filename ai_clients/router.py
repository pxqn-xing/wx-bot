#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI 路由器
负责根据不同类型的请求，将请求转发至相应的 AI 服务
"""

import logging
import re
from config import (
    USE_ARK_API, COZE_TRIGGER_KEYWORDS, COZE_DATABASE_KEYWORDS,
    GROUP_LIST
)

from ai_clients.deepseek import get_deepseek_response
from ai_clients.ark import get_ark_response
from ai_clients.coze import get_coze_response
from ai_clients.moonshot import recognize_image_with_moonshot

logger = logging.getLogger(__name__)

# 合并所有 Coze 关键词（此处仍保留，供其它地方参考）
COZE_KEY_WORDS = COZE_TRIGGER_KEYWORDS + COZE_DATABASE_KEYWORDS


def get_ai_response(message, user_id, intention_key):
    """
    AI 响应路由器
    根据消息内容、用户 ID 及意图关键词，将请求路由到不同的 AI 服务

    Args:
        message (str): 用户消息内容
        user_id (str): 用户 ID
        intention_key (str): 意图识别关键词，取值可能为 "Constellation" 或 "None"

    Returns:
        str: AI 响应内容
    """
    # 去除前后空白字符
    stripped_message = message.strip()

    # 签到功能
    if "签到" in message:
        # 延迟导入，避免循环导入
        from user.services import perform_sign_in
        return perform_sign_in(user_id)

    # 查询金币余额
    elif "金币余额" in message:
        # 延迟导入，避免循环导入
        from user.services import query_coin_balance
        return query_coin_balance(user_id)

    # 处理图片和表情包消息
    elif "发送了图片：" in message or "发送了表情包：" in message:
        logger.info("检测到图片或表情包消息，直接返回消息内容（移除时间戳）")
        # 使用正则表达式移除时间戳 [YYYY-MM-DD HH:MM:SS]
        cleaned_message = re.sub(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] ', '', message)
        return cleaned_message

    # 判断是否为群聊消息
    is_group_chat = user_id in GROUP_LIST
    
    # 优先根据意图识别结果决定调用哪个服务，但只对群聊进行意图识别
    if is_group_chat and intention_key == "Constellation":
        logger.info("群聊消息，意图识别结果为 'Constellation'，调用 Coze API")
        return get_coze_response(message, user_id)
    else:
        if is_group_chat:
            logger.info("群聊消息，意图识别结果为 'None'，调用其他服务")
        else:
            logger.info("私聊消息，直接调用 AI 服务，不进行意图识别")
            
        # 根据配置选择使用火山方舟或 DeepSeek
        if USE_ARK_API:
            logger.info(f"使用火山方舟 API 处理请求: {message}")
            return get_ark_response(message, user_id, intention_key if is_group_chat else "None")
        else:
            logger.info(f"使用 DeepSeek API 处理请求: {message}")
            return get_deepseek_response(message, user_id, intention_key if is_group_chat else "None")
