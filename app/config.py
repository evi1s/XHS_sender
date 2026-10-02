
"""
配置文件
--------------------------
这里定义了整个应用所需的所有配置，包括数据库连接信息和各个模块配置。
当需要修改配置时，只应修改此文件。
"""

import os

# ==============================================================================
PROXY_SERVER_URL = os.getenv("PROXY_SERVER_URL", "http://your-server.example.com/execute-task")
PROXY_API_KEY = os.getenv("PROXY_API_KEY", "xhs_zLri9Y4VQSbdU1hQXhCUDkXsfZKPXlCrmWhsQ9nJ")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "GysaYRLWjDBAJSkM")

# ==============================================================================
MONGO_HOST = os.getenv("MONGO_HOST", "mongo")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGO_USERNAME = os.getenv("MONGO_USERNAME", "user_zBMry8vp")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "APj8fKmn32Vahqsx")
MONGO_AUTH_SOURCE = os.getenv("MONGO_AUTH_SOURCE", "admin")

# ==============================================================================
MONGO_DB_NAME = 'xhs_demo'
MONGO_MEMBER_COLLECTION = 'member'
MONGO_DEVICE_COLLECTION = os.getenv("MONGO_DEVICE_COLLECTION", "devices_4hbf31")
# MONGO_MASTER_DEVICE_COLLECTION = 'devices'
MONGO_USER_ID_COLLECTION = 'userid'
MONGO_SEND_TEXT_COLLECTION = 'sendtext'
MONGO_COMMENT_COLLECTION = 'sendtext'

# ==============================================================================
SUCCESS_SEND_INTERVAL = 10800  #(秒) 任务成功执行后，该用户的常规冷却时间（2小时），之后才能被再次调度。
FAILURE_COOLDOWN_INTERVAL = 86400  #(秒) 任务连续失败达到最大次数后，该用户的冷却时间（24小时）。
FIRST_FAILURE_COOLDOWN_INTERVAL = 300  #(秒) 任务首次失败的短冷却时间（15秒），给一次重试机会，避免网络临时问题误伤。
FAILURE_COOLDOWN_30_DAYS = 604800  #(秒) 连续两天健康检查都失败后，该用户的冷却时间（30天）。
USER_ID_POLLING_INTERVAL = 60  #(秒) 当任务开始后，如果从数据库中未能获取到【私信接收方】，将等待此时间后重试。
USER_POLLING_INTERVAL = 60  #(秒) 【调度器模式下】，如果没有可用的【发送方账号】，调度器将等待此时间后再次查询。
MAX_RETRY_ATTEMPTS = 2  #(次) 单个任务流程（含领取接收方）的最大重试次数。账号每日测活次数已硬编码为 2，见 main_sse.py 的 MAX_PROBE_ATTEMPTS。
MAX_DAILY_USAGE = 1  #(次) 每个userid每天最大使用次数。
TASK_INTERVAL = 35  #(秒)

# ==============================================================================
SEND_MODE_CARD_ONLY = 1
SEND_MODE_TEXT_ONLY = 2
SEND_MODE_CARD_AND_TEXT = 3
SEND_MODE_CARD2_ONLY = 4
CARD_AND_TEXT_CARD = 1  #卡片+文本模式使用的卡片: 1=卡片1(xhs3.json), 2=卡片2(xhs2.json)
MESSAGE_SEND_MODE = 2  #<修改此处的数字来切换模式 (1=卡片1, 2=文本, 3=卡片+文本, 4=卡片2)

# ==============================================================================
# 健康检查的云托管监测号（可选）：填写后优先生效；留空则使用服务端 sconfig.py 中配置的监测号。
CHECK_USER_ID = os.getenv('CHECK_USER_ID', '')
