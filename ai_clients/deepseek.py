#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DeepSeek API 客户端
"""

import logging
import os
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL, TEMPERATURE, MAX_TOKEN
from utils.chat_context_manager import get_recent_conversation, save_chat_record

logger = logging.getLogger(__name__)

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
)

def get_user_prompt(user_id, intention_key, root_dir):
    """
    获取用户的自定义 Prompt，如果不存在则使用默认的 prompt.md

    Args:
        user_id (str): 用户ID
        intention_key (str): 意图关键词
        root_dir (str): 项目根目录

    Returns:
        str: Prompt 内容
    """
    if "None" in intention_key:
        prompt_path = os.path.join(root_dir, 'prompt', f'{user_id}.md')
    elif "Constellation" in intention_key:
        prompt_path = os.path.join(root_dir, 'prompt', f'{intention_key}.md')
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read()
    else:
        with open(os.path.join(root_dir, 'prompt.md'), 'r', encoding='utf-8') as file:
            return file.read()

def get_deepseek_response(message, user_id, intention_key, root_dir=None):
    """
    调用 DeepSeek API 获取回复，整合数据库上下文信息

    Args:
        message (str): 用户消息
        user_id (str): 用户ID
        intention_key (str): 意图关键词
        root_dir (str, optional): 项目根目录，用于加载 Prompt 文件

    Returns:
        str: DeepSeek 模型的回复
    """
    try:
        logger.info(f"调用 DeepSeek API - 用户ID: {user_id}, 消息: {message}")

        if root_dir:
            user_prompt = get_user_prompt(user_id, intention_key, root_dir)
        else:
            user_prompt = "你是一个有用的AI助手。"
            try:
                with open('prompt.md', 'r', encoding='utf-8') as file:
                    user_prompt = file.read()
            except FileNotFoundError:
                logger.warning("未找到 prompt.md 文件，使用默认 Prompt")

        # 从数据库获取用户最近对话记录（上下文）
        conversation_context = get_recent_conversation(user_id, limit=30)
        # 构造系统提示（system message），包含用户的自定义 Prompt 与历史对话
        system_message = f"{user_prompt}\n\n历史对话记录：\n{conversation_context}" if conversation_context else user_prompt

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": message}
        ]

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKEN,
            stream=False
        )

        if not response.choices:
            logger.error("API 返回空 choices")
            return "服务响应异常，请稍后再试"

        reply = response.choices[0].message.content.strip()

        # 保存当前对话记录到数据库
        save_chat_record(user_id, user_id, message, reply)

        logger.info(f"DeepSeek API 回复: {reply}")
        return reply
    except Exception as e:
        logger.error(f"DeepSeek 调用失败: {str(e)}", exc_info=True)
        return "抱歉，我现在有点忙，稍后再聊吧。"
