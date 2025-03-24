import base64
import json

import requests
import logging
from datetime import datetime, time as dt_time
import threading
import time
import os

from database import Session, ChatMessage
from wxauto import WeChat
from openai import OpenAI
import random
from typing import Optional
import pyautogui
import shutil
from models import GameUser
import logging
from config import (
    DEEPSEEK_API_KEY, MAX_TOKEN, TEMPERATURE, MODEL, DEEPSEEK_BASE_URL, LISTEN_LIST,
    MOONSHOT_API_KEY, MOONSHOT_BASE_URL, MOONSHOT_TEMPERATURE, EMOJI_DIR,
    AUTO_MESSAGE, MIN_COUNTDOWN_HOURS, MAX_COUNTDOWN_HOURS, MOONSHOT_MODEL,
    QUIET_TIME_START, QUIET_TIME_END, ARK_API_KEY, ARK_MODEL, ARK_BASE_URL, USE_ARK_API, BOT_NAME, GROUP_LIST,
    COZE_API_KEY, COZE_BOT_ID, COZE_API_ENDPOINT, COZE_TRIGGER_KEYWORDS,COZE_DATABASE_KEYWORDS
)

# 获取微信窗口对象
wx = WeChat()
# 设置监听列表（LISTEN_LIST在config.py中配置）
listen_list = LISTEN_LIST + GROUP_LIST
# 循环添加监听对象
for i in listen_list:
    wx.AddListenChat(who=i, savepic=True)
# 持续监听消息，并且收到消息后回复
wait = 1  # 设置1秒查看一次是否有新消息

# 初始化OpenAI客户端
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
)

# 获取程序根目录
root_dir = os.path.dirname(os.path.abspath(__file__))

# 用户消息队列和聊天上下文管理
user_queues = {}  # {user_id: {'messages': [], 'last_message_time': 时间戳, ...}}
queue_lock = threading.Lock()  # 队列访问锁
chat_contexts = {}  # {user_id: [{'role': 'user', 'content': '...'}, ...]}

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

COZE_KEY_WORDS = COZE_TRIGGER_KEYWORDS + COZE_DATABASE_KEYWORDS

# 存储用户的计时器和随机等待时间
user_timers = {}
user_wait_times = {}
emoji_timer = None
emoji_timer_lock = threading.Lock()
# 全局变量，控制消息发送状态
can_send_messages = True
is_sending_message = False

def parse_time(time_str):
    return datetime.strptime(time_str, "%H:%M").time()


quiet_time_start = parse_time(QUIET_TIME_START)
quiet_time_end = parse_time(QUIET_TIME_END)


def check_user_timeouts():
    while True:
        current_time = time.time()
        for user in listen_list:
            last_active = user_timers.get(user)
            wait_time = user_wait_times.get(user)
            if last_active and wait_time:
                if current_time - last_active >= wait_time:
                    if not is_quiet_time():
                        reply = get_ai_response(AUTO_MESSAGE, user)
                        send_reply(user, user, user, AUTO_MESSAGE, reply)
                    # 重置计时器和等待时间
                    reset_user_timer(user)
        time.sleep(10)  # 每10秒检查一次


def reset_user_timer(user):
    user_timers[user] = time.time()
    user_wait_times[user] = get_random_wait_time()


def get_random_wait_time():
    return random.uniform(MIN_COUNTDOWN_HOURS, MAX_COUNTDOWN_HOURS) * 3600  # 转换为秒


# 当接收到用户的新消息时，调用此函数
def on_user_message(user):
    if user not in listen_list:
        listen_list.append(user)
    reset_user_timer(user)


def save_message(sender_id, sender_name, message, reply):
    # 保存聊天记录到数据库
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
    except Exception as e:
        logger.error(f"保存消息失败: {str(e)}")


def query_coin_balance(user_id: str) -> str:
    """添加签到日期的信息展示"""
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
    finally:
        session.close()

from datetime import datetime, timezone, timedelta


def perform_sign_in(user_id: str) -> str:
    """
    签到功能加强版：每天只能签到一次
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


def get_user_prompt(user_id):
    # 动态获取用户的Prompt，如果不存在则使用默认的prompt.md
    prompt_path = os.path.join(root_dir, 'prompts', f'{user_id}.md')
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read()
    else:
        # 加载默认的prompt.md
        with open(os.path.join(root_dir, 'prompt.md'), 'r', encoding='utf-8') as file:
            return file.read()


def get_deepseek_response(message, user_id):
    try:
        logger.info(f"调用 DeepSeek API - 用户ID: {user_id}, 消息: {message}")
        user_prompt = get_user_prompt(user_id)
        with queue_lock:
            if user_id not in chat_contexts:
                chat_contexts[user_id] = []
            chat_contexts[user_id].append({"role": "user", "content": message})

        MAX_GROUPS = 5
        while len(chat_contexts[user_id]) > MAX_GROUPS * 2:
            chat_contexts[user_id].pop(0)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": user_prompt},
                *chat_contexts[user_id][-MAX_GROUPS * 2:]
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKEN,
            stream=False
        )

        if not response.choices:
            logger.error("API返回空choices")
            return "服务响应异常，请稍后再试"

        reply = response.choices[0].message.content.strip()
        with queue_lock:
            chat_contexts[user_id].append({"role": "assistant", "content": reply})

        logger.info(f"API回复: {reply}")

        return reply
    except Exception as e:
        logger.error(f"DeepSeek调用失败: {str(e)}", exc_info=True)
        return "抱歉，我现在有点忙，稍后再聊吧。"


def get_ark_response(message, user_id):
    try:
        logger.info(f"调用火山方舟API-用户ID:{user_id},消息：{message}")

        # 确保上下文初始化（关键修复点）
        with queue_lock:
            if user_id not in chat_contexts:
                chat_contexts[user_id] = []

            # 维护上下文队列长度
            max_groups = 5  # 保持与DeepSeek相同配置
            while len(chat_contexts[user_id]) > max_groups * 2:
                chat_contexts[user_id].pop(0)

            # 添加新用户输入到上下文
            chat_contexts[user_id].append({"role": "user", "content": message})

            # 构建有效历史记录
            valid_history = chat_contexts[user_id][-max_groups * 2:]

        headers = {
            "Authorization": f"Bearer {ARK_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": ARK_MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": get_user_prompt(user_id)},
                *valid_history  # 改为使用维护后的历史记录
            ]
        }

        response = requests.post(
            f"{ARK_BASE_URL}/bots/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )

        if response.status_code != 200:
            logger.error(f"火山API错误[{response.status_code}]:{response.text}")
            return "服务器响应异常，请稍后再试"

        result = response.json()
        if not result.get('choices'):
            logger.error("火山API返回异常结构")
            return "服务器响应异常，请稍后再试"

        reply = result['choices'][0]['message']['content'].strip()

        with queue_lock:
            if user_id not in chat_contexts:
                chat_contexts[user_id] = []
            chat_contexts[user_id].append({"role": "assistant", "content": reply})

        logger.info(f"火山API回复：{reply}")
        return reply
    except Exception as e:
        logger.info(f"火山API调用失败：{str(e)}", exc_info=True)
        return "暂时无法回复，请稍后再试"


def get_coze_response(message, user_id, conversation_id=None):
    try:
        logger.info(f"调用CozeAPI - 用户:{user_id}, 会话:{conversation_id}")
        headers = {
            "Authorization": f"Bearer {COZE_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        data = {
            "bot_id": COZE_BOT_ID,
            "user_id": user_id,
            "stream": True,
            "auto_save_history": True,
            "additional_messages": [{
                "role": "user",
                "content": message,
                "content_type": "text"
            }]
        }

        # 构造带conversation_id的URL
        endpoint = COZE_API_ENDPOINT
        if conversation_id:
            endpoint += f"?conversation_id={conversation_id}"

        full_response = []
        buffer = ""
        start_time = time.time()

        with requests.post(endpoint, headers=headers, json=data, stream=True, timeout=30) as response:
            response.raise_for_status()

            for chunk in response.iter_content(chunk_size=1024):
                if time.time() - start_time > 30:
                    raise TimeoutError("响应超时")

                buffer += chunk.decode('utf-8')
                while "\n\n" in buffer:
                    event_block, buffer = buffer.split("\n\n", 1)
                    event_type = None
                    data_json = None

                    # 解析事件块
                    for line in event_block.split('\n'):
                        line = line.strip()
                        if line.startswith("event:"):
                            event_type = line.split(":", 1)[1].strip()
                        elif line.startswith("data:"):
                            data_part = line.split(":", 1)[1].strip()
                            try:
                                data_json = json.loads(data_part)
                            except json.JSONDecodeError:
                                logger.warning(f"无效JSON数据: {data_part}")

                    # 处理事件
                    if data_json:
                        if event_type == "conversation.message.delta":
                            full_response.append(data_json.get("content", ""))
                        elif event_type == "conversation.message.completed":
                            if data_json.get("type") == "answer":
                                full_response = [data_json.get("content", "")]
                                return "".join(full_response).strip()
                        elif event_type == "done":
                            break

        return "".join(full_response).strip() or "暂无回复"

    except TimeoutError:
        logger.warning("Coze API响应超时")
        return "请求超时，请重试"
    except Exception as e:
        logger.error(f"API调用异常: {str(e)}", exc_info=True)
        return "服务暂时不可用"


def get_ai_response(message, user_id):
    # 去除前后空白字符
    stripped_message = message.strip()

    # 如果消息为签到或金币余额，则直接进行本地数据库操作
    if "签到" in message:
        return perform_sign_in(user_id)
    elif "金币余额" in message:
        return query_coin_balance(user_id)

    # 如果消息包含星座相关关键词，则调用 Coze 智能体回复
    if any(keyword in message for keyword in COZE_TRIGGER_KEYWORDS):
        return get_coze_response(message, user_id)

    # 否则根据配置调用火山方舟或 DeepSeek
    if USE_ARK_API:
        return get_ark_response(message, user_id)
    else:
        return get_deepseek_response(message, user_id)

def message_listener():
    while True:
        try:
            msgs = wx.GetListenMessage()
            for chat in msgs:
                chat_who = chat.who  # 群聊名称或联系人名称
                one_msgs = msgs.get(chat)
                for msg in one_msgs:
                    msgtype = msg.type
                    content = msg.content
                    logger.info(f'【{chat_who}】：{content}')
                    # 此处同时处理私聊和群聊消息（假设群聊消息的类型为'group'或与私聊消息类似）
                    if msgtype in ['friend', 'group']:
                        # 将群聊标识附加到消息对象上
                        msg.chat_who = chat_who
                        if '[动画表情]' in content:
                            handle_emoji_message(msg)
                        else:
                            handle_wxauto_message(msg)
                    else:
                        logger.info(f"忽略非文本消息类型: {msgtype}")
        except Exception as e:
            logger.error(f"消息监听出错: {str(e)}")
        time.sleep(wait)


def recognize_image_with_moonshot(image_path, is_emoji=False):
    # 先暂停向DeepSeek API发送消息队列
    global can_send_messages
    can_send_messages = False

    """使用Moonshot AI识别图片内容并返回文本"""
    with open(image_path, 'rb') as img_file:
        image_content = base64.b64encode(img_file.read()).decode('utf-8')
    headers = {
        'Authorization': f'Bearer {MOONSHOT_API_KEY}',
        'Content-Type': 'application/json'
    }
    text_prompt = "请描述这个图片" if not is_emoji else "请描述这个聊天窗口的最后一张表情包"
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
    try:
        response = requests.post(f"{MOONSHOT_BASE_URL}/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        recognized_text = result['choices'][0]['message']['content']
        if is_emoji:
            # 如果recognized_text包含“最后一张表情包是”，只保留后面的文本
            if "最后一张表情包是" in recognized_text:
                recognized_text = recognized_text.split("最后一张表情包是", 1)[1].strip()
            recognized_text = "发送了表情包：" + recognized_text
        else:
            recognized_text = "发送了图片：" + recognized_text
        logger.info(f"Moonshot AI图片识别结果: {recognized_text}")
        # 恢复向Deepseek发送消息队列
        can_send_messages = True
        return recognized_text

    except Exception as e:
        logger.error(f"调用Moonshot AI识别图片失败: {str(e)}")
        # 恢复向Deepseek发送消息队列
        can_send_messages = True
        return ""


def handle_emoji_message(msg):
    global emoji_timer
    global can_send_messages
    can_send_messages = False

    def timer_callback():
        with emoji_timer_lock:
            handle_wxauto_message(msg)
            emoji_timer = None

    with emoji_timer_lock:
        if emoji_timer is not None:
            emoji_timer.cancel()
        emoji_timer = threading.Timer(3.0, timer_callback)
        emoji_timer.start()


def handle_wxauto_message(msg):
    try:
        # 如果消息来自群聊，则 chat_target 为群聊名称，否则为发送者的昵称
        sender_name = msg.sender  # 实际发送者的昵称
        chat_target = getattr(msg, 'chat_who', sender_name)

        # 获取消息内容，并处理@机器人的情况
        content = getattr(msg, 'content', None) or getattr(msg, 'text', None)
        if not content:
            logger.warning("无法获取消息内容")
            return

        # 如果消息来自群聊，检查是否包含@BOT_NAME
        if chat_target in GROUP_LIST:
            # 改用any()检查是否有Coze触发词
            if not any(keyword in content for keyword in COZE_KEY_WORDS):
                at_tag = f"@{BOT_NAME}"
                if at_tag not in content:
                    logger.info(f"群聊 {chat_target} 消息未包含{at_tag}，忽略回复")
                    return
                else:
                    # 去除所有@机器人的标识
                    content = content.replace(at_tag, "").strip()
            else:
                content = str(content).strip()

        # 重置定时器时使用 chat_target 作为用户标识
        on_user_message(chat_target)

        # 添加时间戳，保存到队列
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"[{current_time}] {content}"
        logger.info(f"处理消息 - {chat_target}: {content}")

        with queue_lock:
            if chat_target not in user_queues:
                user_queues[chat_target] = {
                    'messages': [content],
                    'sender_name': sender_name,
                    'username': chat_target,
                    'last_message_time': time.time()
                }
                logger.info(f"已为 {chat_target} 初始化消息队列")
            else:
                if len(user_queues[chat_target]['messages']) >= 5:
                    user_queues[chat_target]['messages'].pop(0)
                user_queues[chat_target]['messages'].append(content)
                user_queues[chat_target]['last_message_time'] = time.time()
                logger.info(f"{chat_target} 的消息已加入队列并更新最后消息时间")
    except Exception as e:
        logger.error(f"消息处理失败: {str(e)}")


def check_inactive_users():
    global can_send_messages
    while True:
        current_time = time.time()
        inactive_users = []
        with queue_lock:
            for username, user_data in user_queues.items():
                last_time = user_data.get('last_message_time', 0)
                if current_time - last_time > 7 and can_send_messages and not is_sending_message:
                    inactive_users.append(username)

        for username in inactive_users:
            process_user_messages(username)

        time.sleep(1)  # 每秒检查一次


def process_user_messages(user_id):
    global can_send_messages
    with queue_lock:
        if user_id not in user_queues:
            return
        user_data = user_queues.pop(user_id)
        messages = user_data['messages']
        sender_name = user_data['sender_name']
        username = user_data['username']

    # 合并消息为一句
    merged_message = ' '.join(messages)
    logger.info(f"处理合并消息 ({sender_name}): {merged_message}")

    # 将消息发送给智能体处理（智能体内部会调用小游戏接口并返回回复）
    reply = get_ai_response(merged_message, user_id)

    # 若使用Deepseek R1，则只保留思考结果
    if "</think>" in reply:
        reply = reply.split("</think>", 1)[1].strip()

    # 使用与群聊回复一致的 send_reply 进行回复
    send_reply(user_id, sender_name, username, merged_message, reply)


def send_reply(user_id, sender_name, username, merged_message, reply):
    """
    修改后的发送回复函数：
    若 user_id 在 GROUP_LIST 中，则说明该消息来自群聊，回复目标即为群聊名称；
    否则，回复目标为发送者（sender_name）
    """
    global is_sending_message
    try:
        is_sending_message = True

        # 判断回复目标：如果 user_id 在 GROUP_LIST 中，则使用 user_id，否则使用 sender_name
        target = user_id if user_id in GROUP_LIST else sender_name

        # 先检查是否需要发送表情包
        if is_emoji_request(merged_message) or is_emoji_request(reply):
            emoji_path = get_random_emoji()
            if emoji_path:
                try:
                    wx.SendFiles(filepath=emoji_path, who=target)
                except Exception as e:
                    logger.error(f"发送表情包失败: {str(e)}")

        if '\\' in reply:
            parts = [p.strip() for p in reply.split('\\') if p.strip()]
            for i, part in enumerate(parts):
                wx.SendMsg(part, target)
                logger.info(f"分段回复 {sender_name}: {part}")
                if i < len(parts) - 1:
                    next_part = parts[i + 1]
                    average_typing_speed = 0.1
                    delay = len(next_part) * (average_typing_speed + random.uniform(0.05, 0.15))
                    time.sleep(delay)
        else:
            wx.SendMsg(reply, target)
            logger.info(f"回复 {sender_name}: {reply}")

        is_sending_message = False
    except Exception as e:
        logger.error(f"发送回复失败: {str(e)}")
        is_sending_message = False

    save_message(username, sender_name, merged_message, reply)


def is_emoji_request(text: str) -> bool:
    """
    判断是否为表情包请求
    """
    # 直接请求表情包的关键词
    emoji_keywords = ["表情包", "表情", "斗图", "gif", "动图"]

    emotion_keywords = ["开心", "难过", "生气", "委屈", "高兴", "伤心",
                        "哭", "笑", "怒", "喜", "悲", "乐", "泪", "哈哈",
                        "呜呜", "嘿嘿", "嘻嘻", "哼", "啊啊", "呵呵", "可爱",
                        "惊讶", "惊喜", "恐惧", "害怕", "紧张", "放松", "激动",
                        "满足", "失望", "愤怒", "羞愧", "兴奋", "愉快", "心酸",
                        "愧疚", "懊悔", "孤独", "寂寞", "安慰", "安宁", "放心",
                        "烦恼", "忧虑", "疑惑", "困惑", "怀疑", "鄙视", "厌恶",
                        "厌倦", "失落", "愉悦", "激动", "惊恐", "惊魂未定", "震惊"]

    # 检查直接请求
    if any(keyword in text.lower() for keyword in emoji_keywords):
        return True

    # 检查情感表达
    if any(keyword in text for keyword in emotion_keywords):
        return True

    return False


def get_random_emoji() -> Optional[str]:
    """
    从表情包目录随机获取一个表情包
    """
    try:
        emoji_dir = os.path.join(root_dir, EMOJI_DIR)
        if not os.path.exists(emoji_dir):
            logger.error(f"表情包目录不存在: {emoji_dir}")
            return None

        emoji_files = [f for f in os.listdir(emoji_dir)
                       if f.lower().endswith(('.gif', '.jpg', '.png', '.jpeg'))]

        if not emoji_files:
            return None

        random_emoji = random.choice(emoji_files)
        return os.path.join(emoji_dir, random_emoji)
    except Exception as e:
        logger.error(f"获取表情包失败: {str(e)}")
        return None


def capture_and_save_screenshot(who):
    screenshot_folder = os.path.join(root_dir, 'screenshot')
    if not os.path.exists(screenshot_folder):
        os.makedirs(screenshot_folder)
    screenshot_path = os.path.join(screenshot_folder, f'{who}_{datetime.now().strftime("%Y%m%d%H%M%S")}.png')

    try:
        # 激活并定位微信聊天窗口
        wx_chat = WeChat()
        wx_chat.ChatWith(who)
        chat_window = pyautogui.getWindowsWithTitle(who)[0]

        # 确保窗口被前置和激活
        if not chat_window.isActive:
            chat_window.activate()
        if not chat_window.isMaximized:
            chat_window.maximize()

        # 获取窗口的坐标和大小
        x, y, width, height = chat_window.left, chat_window.top, chat_window.width, chat_window.height

        time.sleep(wait)

        # 截取指定窗口区域的屏幕
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        screenshot.save(screenshot_path)
        logger.info(f'已保存截图: {screenshot_path}')
        return screenshot_path
    except Exception as e:
        logger.error(f'保存截图失败: {str(e)}')


def clean_up_temp_files():
    # 检查是否存在该目录
    if os.path.isdir("screenshot"):
        shutil.rmtree("screenshot")
        print(f"目录 screenshot 已成功删除")
    else:
        print(f"目录 screenshot 不存在，无需删除")

    if os.path.isdir("wxauto文件"):
        shutil.rmtree("wxauto文件")
        print(f"目录 wxauto文件 已成功删除")
    else:
        print(f"目录 wxauto文件 不存在，无需删除")


def is_quiet_time():
    current_time = datetime.now().time()
    if quiet_time_start <= quiet_time_end:
        return quiet_time_start <= current_time <= quiet_time_end
    else:
        return current_time >= quiet_time_start or current_time <= quiet_time_end


def main():
    try:
        clean_up_temp_files()

        global wx
        wx = WeChat()

        listener_thread = threading.Thread(target=message_listener)
        listener_thread.daemon = True
        listener_thread.start()

        checker_thread = threading.Thread(target=check_inactive_users)
        checker_thread.daemon = True
        checker_thread.start()

        # 启动后台线程来检查用户超时
        # threading.Thread(target=check_user_timeouts, daemon=True).start()

        logger.info("开始运行BOT...")

        while True:
            time.sleep(wait)
    except Exception as e:
        logger.error(f"发生异常: {str(e)}")
    finally:
        logger.info("程序退出")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("用户终止程序")
    except Exception as e:
        logger.error(f"发生异常: {str(e)}", exc_info=True)