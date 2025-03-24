#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用户管理器
负责管理用户消息队列、超时检查和自动消息发送
"""

import logging
import random
import threading
import time
import os
import re
from datetime import datetime
from typing import Dict, List, Any

from database import Session, ChatMessage
from config import (
    AUTO_MESSAGE, MIN_COUNTDOWN_HOURS, MAX_COUNTDOWN_HOURS,
    LISTEN_LIST, GROUP_LIST
)
from ai_clients.moonshot import can_send_messages, recognize_image_with_moonshot
from utils.time_utils import is_quiet_time

logger = logging.getLogger(__name__)


def get_intention_key(message, root_dir):
    """
    调用意图识别专家，根据消息内容返回意图关键词
    使用 prompt/Constellation.md 文件作为提示词来识别星座相关消息
    当前的意图识别专家输出 "Constellation" 或 "None"

    Args:
        message (str): 用户消息内容
        root_dir (str): 项目根目录路径

    Returns:
        str: 意图关键词
    """
    prompt_file = os.path.join(root_dir, 'prompt', 'Constellation.md')
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_content = f.read()
        logger.info("成功加载意图识别专家的定位文件")
    except Exception as e:
        logger.error(f"加载意图识别专家定位文件失败: {str(e)}")
        prompt_content = ""

    # 简单的星座关键词识别逻辑 (实际应该使用NLP模型)
    constellation_keywords = [
        "星座", "白羊", "金牛", "双子", "巨蟹", "狮子", "处女", 
        "天秤", "天蝎", "射手", "摩羯", "水瓶", "双鱼", 
        "运势", "星盘", "水逆", "太阳星座", "上升星座", "星座配对", "占星"
    ]
    
    for keyword in constellation_keywords:
        if keyword in message:
            return "Constellation"
    return "None"

class UserManager:
    """用户管理器"""

    def __init__(self, sender):
        """
        初始化用户管理器

        Args:
            sender: 微信消息发送器
        """
        self.sender = sender
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 用户消息队列
        self.user_queues = {}  # {user_id: {'messages': [], 'last_message_time': 时间戳, ...}}
        self.queue_lock = threading.Lock()

        # 用户定时器
        self.user_timers = {}  # {user_id: 上次活跃时间}
        self.user_wait_times = {}  # {user_id: 随机等待时间}

        # 表情包定时器
        self.emoji_timer = None
        self.emoji_timer_lock = threading.Lock()

        # 消息发送状态控制
        self.is_sending_message = False

        # 监听用户列表
        self.listen_list = LISTEN_LIST + GROUP_LIST

        logger.info("用户管理器初始化完成")

    def on_user_message(self, user):
        """
        处理用户新消息，重置用户定时器

        Args:
            user (str): 用户ID
        """
        if user not in self.listen_list:
            self.listen_list.append(user)
            logger.info(f"添加新用户到监听列表: {user}")
        self.reset_user_timer(user)

    def reset_user_timer(self, user):
        """
        重置用户的定时器和等待时间

        Args:
            user (str): 用户ID
        """
        self.user_timers[user] = time.time()
        self.user_wait_times[user] = self.get_random_wait_time()
        logger.debug(f"重置用户 {user} 的定时器，等待时间: {self.user_wait_times[user]/3600:.2f}小时")

    def get_random_wait_time(self):
        """
        获取随机等待时间

        Returns:
            float: 随机等待时间（秒）
        """
        return random.uniform(MIN_COUNTDOWN_HOURS, MAX_COUNTDOWN_HOURS) * 3600

    def check_user_timeouts(self):
        """
        检查用户超时，发送自动消息
        持续运行的后台线程
        """
        while True:
            current_time = time.time()
            for user in self.listen_list:
                last_active = self.user_timers.get(user)
                wait_time = self.user_wait_times.get(user)
                if last_active and wait_time:
                    if current_time - last_active >= wait_time:
                        if not is_quiet_time():
                            logger.info(f"用户 {user} 超时，发送自动消息")
                            # 在使用时导入get_ai_response，避免循环导入
                            from ai_clients.router import get_ai_response
                            reply = get_ai_response(AUTO_MESSAGE, user, "None")
                            self.sender.send_reply(user, user, user, AUTO_MESSAGE, reply)
                        # 重置计时器和等待时间
                        self.reset_user_timer(user)
            time.sleep(10)  # 每10秒检查一次

    def check_inactive_users(self):
        """
        检查不活跃用户，处理消息队列
        持续运行的后台线程
        """
        while True:
            current_time = time.time()
            inactive_users = []

            with self.queue_lock:
                for username, user_data in self.user_queues.items():
                    last_time = user_data.get('last_message_time', 0)
                    if (current_time - last_time > 7 and
                        can_send_messages and
                        not self.is_sending_message):
                        inactive_users.append(username)

            for username in inactive_users:
                self.process_user_messages(username)

            time.sleep(1)  # 每秒检查一次

    def handle_message(self, msg):
        """
        处理微信消息

        Args:
            msg: 微信消息对象
        """
        try:
            # 如果消息来自群聊，则 chat_target 为群聊名称，否则为发送者的昵称
            sender_name = msg.sender  # 实际发送者的昵称
            chat_target = getattr(msg, 'chat_who', sender_name)

            # 获取消息内容
            content = getattr(msg, 'content', None) or getattr(msg, 'text', None)
            if not content:
                logger.warning("无法获取消息内容")
                return

            # 添加时间戳
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            content = f"[{current_time}] {content}"
            logger.info(f"处理消息 - {chat_target}: {content}")

            # 重置用户定时器
            self.on_user_message(chat_target)

            # 添加到消息队列
            with self.queue_lock:
                if chat_target not in self.user_queues:
                    self.user_queues[chat_target] = {
                        'messages': [content],
                        'sender_name': sender_name,
                        'username': chat_target,
                        'last_message_time': time.time()
                    }
                    logger.info(f"已为 {chat_target} 初始化消息队列")
                else:
                    if len(self.user_queues[chat_target]['messages']) >= 5:
                        self.user_queues[chat_target]['messages'].pop(0)
                    self.user_queues[chat_target]['messages'].append(content)
                    self.user_queues[chat_target]['last_message_time'] = time.time()
                    logger.info(f"{chat_target} 的消息已加入队列并更新最后消息时间")
        except Exception as e:
            logger.error(f"消息处理失败: {str(e)}")

    def handle_emoji_message(self, msg):
        """
        处理表情包消息的备用方法
        在无法直接识别表情包图片时使用

        Args:
            msg: 微信表情包消息对象
        """
        try:
            # 获取消息发送者和目标
            sender_name = msg.sender  # 实际发送者的昵称
            chat_target = getattr(msg, 'chat_who', sender_name)
            
            # 重置用户定时器
            self.on_user_message(chat_target)
            
            # 创建表情包回复内容
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            content = f"[{current_time}] 发送了一个表情包，但无法识别具体内容"
            
            # 添加到消息队列处理
            with self.queue_lock:
                if chat_target not in self.user_queues:
                    self.user_queues[chat_target] = {
                        'messages': [content],
                        'sender_name': sender_name,
                        'username': chat_target,
                        'last_message_time': time.time()
                    }
                else:
                    if len(self.user_queues[chat_target]['messages']) >= 5:
                        self.user_queues[chat_target]['messages'].pop(0)
                    self.user_queues[chat_target]['messages'].append(content)
                    self.user_queues[chat_target]['last_message_time'] = time.time()
            
            logger.info(f"处理无法识别的表情包 ({chat_target})")
        except Exception as e:
            logger.error(f"处理表情包消息失败: {str(e)}")

    def process_user_messages(self, user_id):
        """
        处理用户消息队列

        Args:
            user_id (str): 用户 ID
        """
        self.is_sending_message = True
        try:
            with self.queue_lock:
                if user_id not in self.user_queues:
                    self.is_sending_message = False
                    return
                user_data = self.user_queues.pop(user_id)
                messages = user_data['messages']
                sender_name = user_data['sender_name']
                username = user_data['username']

            # 合并消息
            merged_message = ' '.join(messages)
            logger.info(f"处理合并消息 ({sender_name}): {merged_message}")

            # 判断是否为群聊：如果发送者昵称与聊天目标不同，则认为是群聊消息
            if sender_name != username:
                # 调用意图识别专家，获取意图关键词
                intention_key = get_intention_key(merged_message, self.root_dir)
            else:
                intention_key = "None"

            # 在函数内部导入get_ai_response，避免循环导入
            from ai_clients.router import get_ai_response
            # 获取 AI 响应，并传递意图关键词
            reply = get_ai_response(merged_message, user_id, intention_key)

            # 处理 DeepSeek R1 的思考输出（若存在）
            if "</think>" in reply:
                reply = reply.split("</think>", 1)[1].strip()
                
            # 移除回复中的时间戳
            if "发送了图片：" in reply or "发送了表情包：" in reply:
                # 使用正则表达式移除时间戳 [YYYY-MM-DD HH:MM:SS]
                reply = re.sub(r'\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] ', '', reply)
                logger.info(f"已移除图片/表情包回复中的时间戳")

            # 发送回复
            self.sender.send_reply(user_id, sender_name, username, merged_message, reply)
        except Exception as e:
            logger.error(f"处理用户消息失败: {str(e)}")
        finally:
            self.is_sending_message = False

    def save_message(self, sender_id, sender_name, message, reply):
        """
        保存消息到数据库

        Args:
            sender_id (str): 发送者ID
            sender_name (str): 发送者名称
            message (str): 发送的消息
            reply (str): 机器人回复
        """
        try:
            session = Session()
            chat_message = ChatMessage(
                sender_id=sender_id,
                sender_name=sender_name,
                message=message,
                reply=reply
            )
            session.add(chat_message)
            session.commit()
            session.close()
            logger.info(f"消息已保存到数据库: {sender_name}")
        except Exception as e:
            logger.error(f"保存消息失败: {str(e)}")