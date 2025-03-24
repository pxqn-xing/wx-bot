#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
微信消息发送器
负责发送微信消息、表情包等
"""

import logging
import random
import time
import os
import re
from wxauto import WeChat
from config import GROUP_LIST
from utils.emoji_utils import is_emoji_request, get_random_emoji
from utils.chat_context_manager import save_chat_record

logger = logging.getLogger(__name__)

class WeChatSender:
    """微信消息发送器"""

    def __init__(self):
        """初始化微信消息发送器"""
        self.wx = WeChat()
        self.is_sending_message = False
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logger.info("微信消息发送器初始化完成")

    def send_reply(self, user_id, sender_name, username, message, reply):
        """
        发送回复消息

        Args:
            user_id (str): 用户ID
            sender_name (str): 发送者名称
            username (str): 用户名
            message (str): 原始消息
            reply (str): 回复内容
        """
        try:
            self.is_sending_message = True

            # 判断回复目标
            if user_id in GROUP_LIST:
                target = user_id
                reply = f"@{sender_name} {reply}"
            else:
                target = sender_name

            # 检查是否需要发送表情包
            if is_emoji_request(message) or is_emoji_request(reply):
                emoji_path = get_random_emoji(self.root_dir)
                if emoji_path:
                    try:
                        logger.info(f"发送表情包到 {target}: {emoji_path}")
                        self.wx.SendFiles(filepath=emoji_path, who=target)
                    except Exception as e:
                        logger.error(f"发送表情包失败: {str(e)}")

            # 处理Markdown格式的回复
            if '```' in reply or '#' in reply:
                logger.info("检测到可能的Markdown格式内容，进行分段处理")
                segments = self.split_markdown_content(reply)
                for segment in segments:
                    if segment.strip():
                        self.wx.SendMsg(segment, target)
                        logger.info(f"分段回复Markdown内容给 {sender_name}")
                        # 添加延迟，模拟打字速度
                        typing_delay = min(len(segment) * 0.01, 2) + random.uniform(0.5, 1.5)
                        time.sleep(typing_delay)
            # 处理回复文本中可能的分段逻辑
            elif '\\' in reply:
                parts = [p.strip() for p in reply.split('\\') if p.strip()]
                for i, part in enumerate(parts):
                    self.wx.SendMsg(part, target)
                    logger.info(f"分段回复 {sender_name}: {part}")
                    if i < len(parts) - 1:
                        next_part = parts[i + 1]
                        average_typing_speed = 0.1
                        delay = len(next_part) * (average_typing_speed + random.uniform(0.05, 0.15))
                        time.sleep(delay)
            # 处理长文本回复
            elif len(reply) > 500:
                segments = self.split_long_text(reply)
                for segment in segments:
                    if segment.strip():
                        self.wx.SendMsg(segment, target)
                        logger.info(f"长文本分段回复给 {sender_name}")
                        # 添加延迟，模拟打字速度
                        typing_delay = min(len(segment) * 0.01, 2) + random.uniform(0.5, 1.5)
                        time.sleep(typing_delay)
            else:
                self.wx.SendMsg(reply, target)
                logger.info(f"回复 {sender_name}: {reply}")

            # 保存当前对话记录到数据库
            save_chat_record(username, sender_name, message, reply)

        except Exception as e:
            logger.error(f"发送回复失败: {str(e)}")
        finally:
            self.is_sending_message = False
            
    def split_markdown_content(self, content):
        """
        将Markdown内容分段处理
        
        Args:
            content (str): Markdown格式的内容
            
        Returns:
            list: 分段后的内容列表
        """
        # 处理代码块
        if '```' in content:
            # 匹配代码块的正则表达式
            code_block_pattern = r'(```[\s\S]*?```)'
            parts = re.split(code_block_pattern, content)
            
            # 继续处理非代码块部分
            result = []
            for part in parts:
                if part.startswith('```') and part.endswith('```'):
                    # 代码块部分保持完整
                    result.append(part)
                else:
                    # 非代码块部分按段落分割
                    paragraphs = self.split_paragraphs(part)
                    result.extend(paragraphs)
            return result
        else:
            # 没有代码块，直接按段落分割
            return self.split_paragraphs(content)
    
    def split_paragraphs(self, text):
        """
        按段落和标题分割文本
        
        Args:
            text (str): 待分割的文本
            
        Returns:
            list: 分段后的文本列表
        """
        # 按标题和段落分割
        # 匹配标题(#开头)或连续两个换行符
        segments = re.split(r'(?=\n*#)|(?<=\n)\n+(?=\S)', text)
        return [seg.strip() for seg in segments if seg.strip()]
        
    def split_long_text(self, text, max_length=500):
        """
        将长文本分割为适合发送的段落
        
        Args:
            text (str): 待分割的长文本
            max_length (int): 单条消息的最大长度
            
        Returns:
            list: 分段后的文本列表
        """
        # 首先尝试按段落分割
        paragraphs = re.split(r'\n{2,}', text)
        
        result = []
        current_segment = ""
        
        for para in paragraphs:
            # 如果段落本身就超过最大长度，按句子分割
            if len(para) > max_length:
                sentences = re.split(r'(?<=[。！？.!?])\s*', para)
                for sentence in sentences:
                    if len(current_segment) + len(sentence) <= max_length:
                        current_segment += sentence
                    else:
                        if current_segment:
                            result.append(current_segment)
                        current_segment = sentence
            # 段落不超过最大长度，检查与当前段落合并是否会超过
            elif len(current_segment) + len(para) <= max_length:
                if current_segment and not current_segment.endswith("\n"):
                    current_segment += "\n\n" + para
                else:
                    current_segment += para
            else:
                result.append(current_segment)
                current_segment = para
        
        # 添加最后一个段落
        if current_segment:
            result.append(current_segment)
            
        return result
