#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
火山方舟(ARK) API 客户端
"""

import logging
import os
import requests
from config import ARK_API_KEY, ARK_BASE_URL, ARK_MODEL
from utils.chat_context_manager import get_recent_conversation, save_chat_record

logger = logging.getLogger(__name__)

def get_user_prompt(user_id, intention_key, root_dir):
    """
    获取用户的自定义 Prompt，如果不存在则使用默认的 prompt.md
    """
    if "None" in intention_key:
        prompt_path = os.path.join(root_dir, 'prompts', f'{user_id}.md')
    elif "Constellation" in intention_key:
        prompt_path = os.path.join(root_dir, 'prompts', f'{intention_key}.md')

    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read()
    else:
        with open(os.path.join(root_dir, 'prompt.md'), 'r', encoding='utf-8') as file:
            return file.read()

def get_ark_response(message, user_id, intention_key, root_dir=None):
    """
    调用火山方舟(ARK) API 获取回复，整合数据库中的上下文信息

    Args:
        message (str): 用户消息
        user_id (str): 用户ID
        intention_key (str): 意图关键词
        root_dir (str, optional): 项目根目录

    Returns:
        str: 方舟模型的回复
    """
    try:
        logger.info(f"调用火山方舟 API - 用户ID:{user_id}, 消息：{message}")

        if root_dir:
            user_prompt = get_user_prompt(user_id, intention_key, root_dir)
        else:
            user_prompt = "你是一个有用的AI助手。"
            try:
                with open('prompt.md', 'r', encoding='utf-8') as file:
                    user_prompt = file.read()
            except FileNotFoundError:
                logger.warning("未找到 prompt.md 文件，使用默认 Prompt")

        # 获取数据库中的历史对话记录
        conversation_context = get_recent_conversation(user_id, limit=30)
        system_message = f"{user_prompt}\n\n历史对话记录：\n{conversation_context}" if conversation_context else user_prompt

        data = {
            "model": ARK_MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": message}
            ]
        }

        headers = {
            "Authorization": f"Bearer {ARK_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            f"{ARK_BASE_URL}/bots/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )

        if response.status_code != 200:
            logger.error(f"火山API错误[{response.status_code}]:{response.text}")
            return "服务器响应异常，请稍后再试"

        result = response.json()
        if not result.get('choices'):
            logger.error("火山API返回异常结构")
            return "服务器响应异常，请稍后再试"

        reply = result['choices'][0]['message']['content'].strip()

        # 保存当前对话记录到数据库
        save_chat_record(user_id, user_id, message, reply)

        logger.info(f"火山API回复：{reply}")
        return reply
    except Exception as e:
        logger.error(f"火山API调用失败：{str(e)}", exc_info=True)
        return "暂时无法回复，请稍后再试"
