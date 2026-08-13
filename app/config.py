"""
配置文件（Docker 环境变量版）
------------------------------------------------
优先从环境变量读取（由 docker-compose.yml 注入），未设置时使用默认值。
代码中所有 `from config import XXX` 的引用保持不变。
"""

import os


def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# 服务端（向服务商购买）
PROXY_SERVER_URL = os.getenv("PROXY_SERVER_URL", "")
PROXY_API_KEY = os.getenv("PROXY_API_KEY", "")

# Web 控制面板登录
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123456")

# MongoDB 连接（compose 中默认指向 mongo 服务）
MONGO_HOST = os.getenv("MONGO_HOST", "mongo")
MONGO_PORT = _int("MONGO_PORT", 27017)
MONGO_USERNAME = os.getenv("MONGO_USERNAME", "root")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "")
MONGO_AUTH_SOURCE = os.getenv("MONGO_AUTH_SOURCE", "admin")

MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "xhs_demo")
MONGO_MEMBER_COLLECTION = 'member'
MONGO_DEVICE_COLLECTION = 'devices_demo'
# MONGO_MASTER_DEVICE_COLLECTION = 'devices'
MONGO_USER_ID_COLLECTION = 'userid'
MONGO_SEND_TEXT_COLLECTION = 'sendtext'
MONGO_CHECK_STATUS_COLLECTION = 'check_status'
MONGO_COMMENT_COLLECTION = 'sendtext'

# 时间参数（秒）
DEFAULT_SOCKET_TIMEOUT = 30
RECONNECT_DELAY = 2
SUCCESS_SEND_INTERVAL = 7200
FAILURE_COOLDOWN_INTERVAL = 86400
FAILURE_COOLDOWN_30_DAYS = 2592001
INITIAL_MESSAGE_DELAY = 8
USER_ID_POLLING_INTERVAL = 60
USER_POLLING_INTERVAL = 60
MAX_RETRY_ATTEMPTS = 2
MAX_DAILY_USAGE = 2
TASK_INTERVAL = 30

SEND_MODE_CARD_ONLY = 1
SEND_MODE_TEXT_ONLY = 2
SEND_MODE_CARD_AND_TEXT = 3
MESSAGE_SEND_MODE = 2

# 检测号（必须是发送设备之一）
CHECK_USER_ID = os.getenv("CHECK_USER_ID", "")
