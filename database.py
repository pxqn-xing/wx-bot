#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库模块
处理数据库连接和会话管理
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker
from base import Base  # 从 base.py 导入 Base

# 创建数据库引擎
engine = create_engine('sqlite:///game_user.db')

# 创建会话工厂
Session = sessionmaker(bind=engine)

class ChatMessage(Base):
    """聊天消息模型"""
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True)
    sender_id = Column(String(100))  # 发送者微信ID
    sender_name = Column(String(100))  # 发送者昵称
    message = Column(Text)  # 发送的消息
    reply = Column(Text)  # 机器人的回复
    created_at = Column(DateTime, default=datetime.now)

# 确保所有表被创建
def init_db():
    """初始化数据库，创建所有表"""
    # 导入其他模型（这里 GameUser 模型在 models.py 中定义）
    from models import GameUser
    
    # 创建所有数据库表（包括 chat_messages 和 game_users）
    Base.metadata.create_all(engine)
    
    print("数据库初始化完成")

if __name__ == '__main__':
    init_db()
    print("数据库创建成功，新数据库文件为 game_user.db") 