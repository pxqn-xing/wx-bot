#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Coze API 客户端
用于处理星座运势等专用领域的请求
"""

import json
import logging
import time
import codecs
import requests
from config import COZE_API_KEY, COZE_BOT_ID, COZE_API_ENDPOINT

logger = logging.getLogger(__name__)

def get_coze_response(message, user_id, conversation_id=None):
    """
    调用Coze API获取回复
    
    Args:
        message (str): 用户消息
        user_id (str): 用户ID
        conversation_id (str, optional): 会话ID，用于维持多轮对话
        
    Returns:
        str: Coze模型的回复
    """
    try:
        logger.info(f"调用CozeAPI - 用户:{user_id}, 会话:{conversation_id}")
        
        # 准备请求头
        headers = {
            "Authorization": f"Bearer {COZE_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        # 准备请求体
        data = {
            "bot_id": COZE_BOT_ID,
            "user_id": user_id,
            "stream": True,
            "auto_save_history": True,
            "additional_messages": [{
                "role": "user",
                "content": message,
                "content_type": "text"
            }]
        }

        # 构造带 conversation_id 的 URL
        endpoint = COZE_API_ENDPOINT
        if conversation_id:
            endpoint += f"?conversation_id={conversation_id}"

        # 准备响应收集
        full_response = []
        buffer = ""
        start_time = time.time()

        # 创建增量解码器
        decoder = codecs.getincrementaldecoder('utf-8')()

        # 发送请求并处理流式响应
        with requests.post(endpoint, headers=headers, json=data, stream=True, timeout=30) as response:
            response.raise_for_status()

            for chunk in response.iter_content(chunk_size=1024):
                # 检查是否超时
                if time.time() - start_time > 30:
                    raise TimeoutError("响应超时")

                # 使用增量解码器处理分块数据
                buffer += decoder.decode(chunk)
                
                # 处理接收到的事件流
                while "\n\n" in buffer:
                    event_block, buffer = buffer.split("\n\n", 1)
                    event_type = None
                    data_json = None

                    # 解析事件块
                    for line in event_block.split('\n'):
                        line = line.strip()
                        if line.startswith("event:"):
                            event_type = line.split(":", 1)[1].strip()
                        elif line.startswith("data:"):
                            data_part = line.split(":", 1)[1].strip()
                            try:
                                data_json = json.loads(data_part)
                            except json.JSONDecodeError:
                                logger.warning(f"无效JSON数据: {data_part}")

                    # 根据事件类型处理数据
                    if data_json:
                        if event_type == "conversation.message.delta":
                            full_response.append(data_json.get("content", ""))
                        elif event_type == "conversation.message.completed":
                            if data_json.get("type") == "answer":
                                full_response = [data_json.get("content", "")]
                                return "".join(full_response).strip()
                        elif event_type == "done":
                            break

        # 合并所有响应片段
        final_response = "".join(full_response).strip() or "暂无回复"
        logger.info(f"Coze API回复: {final_response}")
        return final_response

    except TimeoutError:
        logger.warning("Coze API响应超时")
        return "请求超时，请重试"
    except Exception as e:
        logger.error(f"Coze API调用异常: {str(e)}", exc_info=True)
        return "服务暂时不可用，请稍后再试" 