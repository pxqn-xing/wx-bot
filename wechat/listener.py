#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
微信消息监听器
负责监听微信消息并分发给用户管理器处理
"""

import logging
import time
import os
from wxauto import WeChat
from config import LISTEN_LIST, GROUP_LIST, BOT_NAME
from ai_clients.moonshot import recognize_image_with_moonshot

logger = logging.getLogger(__name__)


def get_intention_key(content):
    """
    调用意图识别专家，根据消息内容返回意图关键词
    使用 prompt/Constellation.md 文件作为提示词，
    识别消息是否与星座相关，返回 "Constellation" 或 "None"

    Args:
        content (str): 消息内容

    Returns:
        str: 意图关键词
    """
    # 获取项目根目录（当前文件所在目录的上一级）
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
        if keyword in content:
            return "Constellation"
    return "None"


def is_image_path(content):
    """
    判断消息内容是否为图片路径
    
    Args:
        content (str): 消息内容
        
    Returns:
        bool: 是否为图片路径
    """
    # 检查是否是一个文件路径，以及是否包含常见图片扩展名
    image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    return any(ext in content.lower() for ext in image_exts) and ('\\' in content or '/' in content)


class WeChatListener:
    """微信消息监听器"""

    def __init__(self, user_manager):
        """
        初始化微信消息监听器

        Args:
            user_manager: 用户管理器对象
        """
        self.wx = WeChat()
        self.user_manager = user_manager
        self.listen_list = LISTEN_LIST + GROUP_LIST
        self.wait = 1  # 轮询间隔（秒）

        # 为每个联系人/群聊添加监听
        for chat_name in self.listen_list:
            self.wx.AddListenChat(who=chat_name, savepic=True)

        logger.info(f"已初始化微信监听器，监听列表: {self.listen_list}")

    def start(self):
        """
        启动消息监听循环
        持续运行的后台线程
        """
        logger.info("开始监听微信消息")
        while True:
            try:
                msgs = self.wx.GetListenMessage()
                for chat in msgs:
                    chat_who = chat.who  # 群聊名称或联系人名称
                    one_msgs = msgs.get(chat)
                    for msg in one_msgs:
                        msgtype = msg.type
                        content = msg.content
                        logger.info(f'【{chat_who}】：{content} (类型: {msgtype})')

                        # 将群聊标识附加到消息对象上
                        msg.chat_who = chat_who

                        # 处理图片消息 - 检查类型和内容
                        if msgtype == 'picture' or is_image_path(content):
                            logger.info(f"检测到图片消息，来自: {chat_who}")
                            
                            # 获取图片路径
                            img_path = getattr(msg, 'image_path', None)
                            # 如果没有image_path属性但内容是图片路径，直接使用内容
                            if not img_path and is_image_path(content):
                                img_path = content
                                
                            if img_path and os.path.exists(img_path):
                                # 判断是否需要回复图片消息（根据群聊规则和@标记）
                                need_reply = True
                                if chat_who in GROUP_LIST:
                                    # 检查群聊图片消息前是否包含@机器人标记
                                    last_msgs = self.wx.GetGroupMsg(chat_who, count=1)
                                    if last_msgs and len(last_msgs) > 0:
                                        last_content = last_msgs[0].content
                                        if f"@{BOT_NAME}" not in last_content:
                                            need_reply = False
                                
                                if need_reply:
                                    # 使用Moonshot AI识别图片内容
                                    is_emoji = '[动画表情]' in content
                                    recognized_text = recognize_image_with_moonshot(img_path, is_emoji)
                                    # 创建新的消息对象，包含识别出的文本
                                    msg.content = recognized_text
                                    self.user_manager.handle_message(msg)
                                else:
                                    logger.info(f"群聊图片消息无需回复，忽略处理")
                            else:
                                logger.warning(f"图片路径不存在或无法访问: {img_path}")
                        # 处理私聊和群聊文本消息
                        elif msgtype in ['friend', 'group']:
                            # 对于群聊消息的处理
                            if chat_who in GROUP_LIST:
                                # 1. 首先使用Constellation.md进行意图识别
                                intention_key = get_intention_key(content)
                                
                                # 2. 如果是星座相关的消息，即使没有@机器人也处理回复
                                if intention_key == "Constellation":
                                    logger.info(f"群聊 {chat_who} 消息被识别为星座相关，将调用Coze进行回复")
                                    # 去除可能包含的@标识，确保纯文本传递给AI
                                    cleaned_content = content.replace(f"@{BOT_NAME}", "").strip()
                                    msg.content = cleaned_content
                                    self.user_manager.handle_message(msg)
                                    continue
                                
                                # 3. 否则，再判断是否@机器人或包含其它触发关键词
                                at_tag = f"@{BOT_NAME}"
                                if at_tag not in content and not self._check_keywords(content):
                                    logger.info(f"群聊 {chat_who} 消息不是星座相关且未包含 {at_tag} 或触发关键词，忽略回复")
                                    continue
                                else:
                                    msg.content = content.replace(at_tag, "").strip()

                            # 处理表情包和普通消息
                            if '[动画表情]' in content:
                                # 检查是否有图片路径
                                img_path = getattr(msg, 'image_path', None)
                                if img_path and os.path.exists(img_path):
                                    # 使用表情包识别模式
                                    recognized_text = recognize_image_with_moonshot(img_path, is_emoji=True)
                                    msg.content = recognized_text
                                    self.user_manager.handle_message(msg)
                                else:
                                    # 找不到图片路径，使用普通表情包处理
                                    logger.warning(f"表情包图片路径不存在，使用常规处理: {img_path}")
                                    self.user_manager.handle_emoji_message(msg)
                            else:
                                self.user_manager.handle_message(msg)
                        else:
                            logger.info(f"忽略消息类型: {msgtype}")
            except Exception as e:
                logger.error(f"消息监听出错: {str(e)}")

            time.sleep(self.wait)

    def _check_keywords(self, content):
        """
        检查消息是否包含触发关键词（不包含星座相关关键词，已在意图识别中处理）

        Args:
            content (str): 消息内容

        Returns:
            bool: 是否包含触发关键词
        """
        keywords = ["金币余额", "签到"]
        return any(keyword in content for keyword in keywords)
