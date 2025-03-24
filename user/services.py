#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
用户服务模块
处理与数据库相关的用户操作，如签到、金币查询等
"""

import logging
from datetime import datetime, timezone, timedelta
from database import Session
from models import GameUser

logger = logging.getLogger(__name__)

def query_coin_balance(user_id: str) -> str:
    """
    查询用户金币余额
    
    Args:
        user_id (str): 用户ID
        
    Returns:
        str: 格式化的余额信息
    """
    session = Session()
    try:
        user = session.query(GameUser).filter_by(id=user_id).first()
        if not user:
            return "您还没有账户，发送【签到】即可创建"

        status = (
            "今日已签到 ✅" if user.last_sign_in_date == datetime.now().date()
            else "今日未签到 ❌"
        )

        return (
            f"💰 金币余额：{user.coin_balance}\n"
            f"📅 签到状态：{status}"
        )
    except Exception as e:
        logger.error(f"查询金币余额失败: {str(e)}")
        return "查询金币余额失败，请稍后再试"
    finally:
        session.close()

def perform_sign_in(user_id: str) -> str:
    """
    用户签到功能
    每天只能签到一次，签到成功后获得10个金币
    
    Args:
        user_id (str): 用户ID
        
    Returns:
        str: 签到结果消息
    """
    session = Session()
    try:
        # 获取中国时区时间（UTC+8）
        tz = timezone(timedelta(hours=8))
        today = datetime.now(tz).date()

        # 查询用户记录
        user = session.query(GameUser).filter_by(id=user_id).first()

        # 用户不存在时初始化
        if not user:
            user = GameUser(
                id=user_id,
                name=user_id,
                coin_balance=0,
                last_sign_in_date=None
            )
            session.add(user)
            session.commit()  # 确保生成用户记录

        # 检查今日是否签到
        if user.last_sign_in_date == today:
            return f"今天已经签到过啦！当前金币余额：{user.coin_balance}"

        # 执行签到
        old_balance = user.coin_balance
        user.coin_balance += 10
        user.last_sign_in_date = today
        session.commit()

        return (
            f"🎉 签到成功！\n"
            f"• 签到前余额：{old_balance}\n"
            f"• 获得奖励：+10\n"
            f"• 当前余额：{user.coin_balance}"
        )

    except Exception as e:
        session.rollback()
        logger.error(f"签到异常 {user_id}: {str(e)}")
        return "签到系统暂时故障，请稍后再试"
    finally:
        session.close() 