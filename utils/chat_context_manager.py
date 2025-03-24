#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
聊天记录管理模块
用于记录用户与机器人之间的对话，并提供查询最近对话的功能，
以便在调用 AI 接口时构造上下文提示，保证回复语气、格式一致。

格式示例：
    用户：你好，今天怎么样？
    机器人：我很好，谢谢你！
    用户：那你觉得天气如何？
    机器人：天气很晴朗……
"""

import logging
from datetime import datetime
from sqlalchemy import desc
from database import Session, ChatMessage

logger = logging.getLogger(__name__)

def save_chat_record(user_id: str, sender_name: str, message: str, reply: str) -> None:
    """
    保存聊天记录到数据库

    Args:
        user_id (str): 用户ID
        sender_name (str): 用户昵称（或发送者名称）
        message (str): 用户消息
        reply (str): 机器人回复
    """
    session = Session()
    try:
        chat_record = ChatMessage(
            sender_id=user_id,
            sender_name=sender_name,
            message=message,
            reply=reply,
            created_at=datetime.now()
        )
        session.add(chat_record)
        session.commit()
        logger.info(f"聊天记录保存成功: {sender_name}")
    except Exception as e:
        logger.error(f"保存聊天记录失败: {e}")
        session.rollback()
    finally:
        session.close()

def get_recent_conversation(user_id: str, limit: int = 30) -> str:
    """
    查询指定用户的最近对话记录，并按照固定格式拼接为对话上下文文本

    Args:
        user_id (str): 用户ID
        limit (int): 获取最近多少条记录，默认为30条

    Returns:
        str: 拼接好的对话上下文文本
    """
    session = Session()
    try:
        # 按创建时间倒序查询最新记录，再反转为正序排列
        records = session.query(ChatMessage)\
            .filter_by(sender_id=user_id)\
            .order_by(desc(ChatMessage.created_at))\
            .limit(limit)\
            .all()
        records.reverse()
        conversation_lines = []
        for record in records:
            conversation_lines.append(f"用户：{record.message}")
            conversation_lines.append(f"机器人：{record.reply}")
        context = "\n".join(conversation_lines)
        logger.info(f"查询到 {len(records)} 条聊天记录，构造上下文成功")
        return context
    except Exception as e:
        logger.error(f"查询聊天记录失败: {e}")
        return ""
    finally:
        session.close()
