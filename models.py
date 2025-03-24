#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库模型模块
定义应用使用的数据库模型
"""

from sqlalchemy import Column, Integer, String, Date
from base import Base

class GameUser(Base):
    """游戏用户模型"""
    __tablename__ = 'game_users'
    
    id = Column(String, primary_key=True)       # 用户ID
    name = Column(String)                       # 用户名
    coin_balance = Column(Integer, default=0)   # 金币余额
    last_sign_in_date = Column(Date)            # 最后一次签到日期 