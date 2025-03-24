#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
表情包处理工具
"""

import os
import random
import logging
from typing import Optional
from config import EMOJI_DIR

logger = logging.getLogger(__name__)

def is_emoji_request(text: str) -> bool:
    """
    判断是否为表情包请求
    
    Args:
        text (str): 需要分析的文本
        
    Returns:
        bool: 是否为表情包请求
    """
    # 直接请求表情包的关键词
    emoji_keywords = ["表情包", "表情", "斗图", "gif", "动图"]

    # 情感表达关键词
    emotion_keywords = [
        "开心", "难过", "生气", "委屈", "高兴", "伤心", "哭", "笑", "怒", 
        "喜", "悲", "乐", "泪", "哈哈", "呜呜", "嘿嘿", "嘻嘻", "哼", 
        "啊啊", "呵呵", "可爱", "惊讶", "惊喜", "恐惧", "害怕", "紧张", 
        "放松", "激动", "满足", "失望", "愤怒", "羞愧", "兴奋", "愉快", 
        "心酸", "愧疚", "懊悔", "孤独", "寂寞", "安慰", "安宁", "放心",
        "烦恼", "忧虑", "疑惑", "困惑", "怀疑", "鄙视", "厌恶", "厌倦", 
        "失落", "愉悦", "激动", "惊恐", "惊魂未定", "震惊"
    ]

    # 检查直接请求
    if any(keyword in text.lower() for keyword in emoji_keywords):
        return True

    # 检查情感表达
    if any(keyword in text for keyword in emotion_keywords):
        return True

    return False

def get_random_emoji(root_dir: str) -> Optional[str]:
    """
    从表情包目录随机获取一个表情包
    
    Args:
        root_dir (str): 项目根目录
        
    Returns:
        Optional[str]: 表情包路径，如果没有找到则返回None
    """
    try:
        emoji_dir = os.path.join(root_dir, EMOJI_DIR)
        if not os.path.exists(emoji_dir):
            logger.error(f"表情包目录不存在: {emoji_dir}")
            return None

        emoji_files = [
            f for f in os.listdir(emoji_dir)
            if f.lower().endswith(('.gif', '.jpg', '.png', '.jpeg'))
        ]

        if not emoji_files:
            logger.warning("表情包目录中没有找到合适的图片文件")
            return None

        random_emoji = random.choice(emoji_files)
        return os.path.join(emoji_dir, random_emoji)
    except Exception as e:
        logger.error(f"获取表情包失败: {str(e)}")
        return None 