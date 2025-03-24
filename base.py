#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库基础模块
定义SQLAlchemy基类
"""

from sqlalchemy.ext.declarative import declarative_base

# 使用 SQLAlchemy 创建基类
Base = declarative_base() 