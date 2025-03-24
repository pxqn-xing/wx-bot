# 微信智能助手

一个模块化设计的微信智能助手，支持多种AI模型接口，具有高扩展性和可维护性。

## 功能特点

- 自动回复微信私聊和群聊消息
- 支持多种AI服务（DeepSeek, 火山方舟, Coze等）
- 表情包自动识别和发送
- 签到和金币系统
- 定时主动消息
- 安静时间段控制

## 项目结构

```
.
├── ai_clients/             # AI服务客户端
│   ├── __init__.py
│   ├── ark.py              # 火山方舟API
│   ├── coze.py             # Coze API
│   ├── deepseek.py         # DeepSeek API
│   ├── moonshot.py         # Moonshot 图像识别
│   └── router.py           # 请求路由分发
├── user/                   # 用户管理
│   ├── __init__.py
│   ├── manager.py          # 用户管理器
│   └── services.py         # 用户服务（签到等）
├── utils/                  # 实用工具
│   ├── __init__.py
│   ├── emoji_utils.py      # 表情包工具
│   ├── image_utils.py      # 图像处理工具
│   └── time_utils.py       # 时间相关工具
├── wechat/                 # 微信操作
│   ├── __init__.py
│   ├── listener.py         # 消息监听
│   └── sender.py           # 消息发送
├── base.py                 # 数据库基础
├── config.py               # 配置文件
├── database.py             # 数据库操作
├── main.py                 # 主程序入口
├── models.py               # 数据库模型
├── prompt.md               # 默认提示词
└── emojis/                 # 表情包目录
```

## 配置说明

编辑 `config.py` 文件，配置以下参数：

- `LISTEN_LIST`: 监听的私聊联系人列表
- `GROUP_LIST`: 监听的群聊列表
- `BOT_NAME`: 机器人在群里的微信昵称
- API配置：根据需要配置DeepSeek, 火山方舟, Coze等API密钥
- `AUTO_MESSAGE`: 定时主动消息的提示词
- `MIN_COUNTDOWN_HOURS`, `MAX_COUNTDOWN_HOURS`: 主动消息的随机等待时间范围
- `QUIET_TIME_START`, `QUIET_TIME_END`: 安静时间段，在此期间不发送主动消息

## 安装与运行

1. 安装依赖:

```bash
pip install -r requirements.txt
```

2. 运行程序:

```bash
python main.py
```

## 自定义提示词

可以为不同用户配置不同的提示词：

1. 在项目根目录创建 `prompts` 文件夹
2. 创建以用户ID命名的markdown文件，如 `prompts/用户名.md`
3. 如果没有找到对应的文件，将使用默认的 `prompt.md`

## 扩展

### 添加新的AI服务

1. 在 `ai_clients` 目录下创建新的客户端文件
2. 在 `ai_clients/__init__.py` 中导出新函数
3. 在 `ai_clients/router.py` 中添加路由逻辑

### 添加新的功能

1. 根据功能类型在对应的模块中添加新代码
2. 在需要的地方引入并使用新功能

## 许可证

基于 GNU GPL-3.0 许可证开源。

## 鸣谢

本项目基于 My-Dream-Moments 项目修改而来。 