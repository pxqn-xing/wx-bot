#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Moonshot API 客户端
用于图像识别，包括表情包和普通图片
"""

import base64
import logging
import requests
from config import MOONSHOT_API_KEY, MOONSHOT_BASE_URL, MOONSHOT_MODEL, MOONSHOT_TEMPERATURE

logger = logging.getLogger(__name__)

# 全局变量，用于控制消息发送队列
can_send_messages = True

def recognize_image_with_moonshot(image_path, is_emoji=False):
    """
    使用Moonshot AI识别图片内容并返回文本描述
    
    Args:
        image_path (str): 图片路径
        is_emoji (bool): 是否为表情包图片
        
    Returns:
        str: 图片描述文本
    """
    # 先暂停向DeepSeek API发送消息队列
    global can_send_messages
    can_send_messages = False
    
    try:
        # 读取图片并转换为base64编码
        with open(image_path, 'rb') as img_file:
            image_content = base64.b64encode(img_file.read()).decode('utf-8')
        
        # 准备请求头
        headers = {
            'Authorization': f'Bearer {MOONSHOT_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # 根据图片类型设置不同的提示文本
        text_prompt = "请描述这个图片" if not is_emoji else "请描述这个聊天窗口的最后一张表情包"
        
        # 准备请求体
        data = {
            "model": MOONSHOT_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_content}"}},
                        {"type": "text", "text": text_prompt}
                    ]
                }
            ],
            "temperature": MOONSHOT_TEMPERATURE
        }
        
        # 发送请求
        logger.info(f"发送图片识别请求到Moonshot API，是否为表情包: {is_emoji}")
        response = requests.post(
            f"{MOONSHOT_BASE_URL}/chat/completions", 
            headers=headers, 
            json=data
        )
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        recognized_text = result['choices'][0]['message']['content']
        
        # 处理识别结果
        if is_emoji:
            # 优化表情包描述
            if "最后一张表情包是" in recognized_text:
                recognized_text = recognized_text.split("最后一张表情包是", 1)[1].strip()
            recognized_text = "发送了表情包：" + recognized_text
        else:
            recognized_text = "发送了图片：" + recognized_text
            
        logger.info(f"Moonshot AI图片识别结果: {recognized_text}")
        # 恢复向DeepSeek发送消息队列
        can_send_messages = True
        return recognized_text

    except Exception as e:
        logger.error(f"调用Moonshot AI识别图片失败: {str(e)}")
        # 恢复向DeepSeek发送消息队列
        can_send_messages = True
        return "图片识别失败，无法获取图片内容" 