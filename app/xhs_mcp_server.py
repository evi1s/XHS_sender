"""
xhs_mcp_server.py
------------------------------------------------
MCP Server：让 Chatbox/Claude 等 MCP 客户端直接调用小红书自动发送任务。

复用 main_sse.py 的核心执行逻辑（DeviceManager / client_main_task），
数据来自本机 MongoDB（设备、接收方、文案），任务通过服务端执行。

启动方式（由 entrypoint.sh 自动启动）：
    python xhs_mcp_server.py
默认监听 0.0.0.0:8090，协议为 streamable-http。

Chatbox 接入：
    设置 -> MCP -> 添加服务器 -> 远程 ->
    URL: http://<服务器IP>:8090/mcp
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from pymongo import MongoClient
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green>|<level>{level: <7}</level>| {message}")

try:
    from fastmcp import FastMCP
except ImportError:
    raise SystemExit("缺少 fastmcp 依赖，请先安装: pip install fastmcp")

import main_sse  # 复用 client_main_task 与 DeviceManager



def _mongo_client():
    return MongoClient(
        f"mongodb://{config.MONGO_HOST}:{config.MONGO_PORT}/",
        username=config.MONGO_USERNAME,
        password=config.MONGO_PASSWORD,
        authSource=config.MONGO_AUTH_SOURCE,
        serverSelectionTimeoutMS=5000,
    )


def _db_collections(client):
    db = client[config.MONGO_DB_NAME]
    return {
        "user_id": db[config.MONGO_USER_ID_COLLECTION],
        "send_text": db[config.MONGO_SEND_TEXT_COLLECTION],
        "comment": db[config.MONGO_COMMENT_COLLECTION],
    }


def _run_scheduler_once():
    """自动调度一轮：领取发送设备 -> 领取接收方 -> 执行发送。"""
    # 先手动探测 Mongo，避免 DeviceManager 内部 sys.exit 杀死 MCP 进程
    try:
        probe = _mongo_client()
        probe.admin.command("ping")
        probe.close()
    except Exception as e:
        return {"status": "error", "message": f"MongoDB 连接失败: {e}"}

    dm = main_sse.DeviceManager()

    checker_config = dm.get_device_by_userid(config.CHECK_USER_ID)
    if not checker_config:
        dm.close()
        return {
            "status": "error",
            "message": f"未在设备集合 '{config.MONGO_DEVICE_COLLECTION}' 中找到检测号 '{config.CHECK_USER_ID}'，请先在控制面板添加检测号设备。",
        }

    claimed = dm.find_available_user_and_claim(config.USER_POLLING_INTERVAL + 120)
    if not claimed:
        dm.close()
        return {"status": "idle", "message": "当前没有可用的发送设备（可能都在冷却期内）。"}

    userid = claimed["userid"]
    mongo_client = _mongo_client()
    try:
        db_collections = _db_collections(mongo_client)
        main_sse.client_main_task(claimed, checker_config, db_collections, dm)
        return {"status": "success", "message": f"任务执行完成（发送设备 {userid}）。"}
    except Exception as e:
        return {"status": "error", "message": f"任务执行失败（发送设备 {userid}）: {type(e).__name__}: {e}"}
    finally:
        try:
            dm.close()
            mongo_client.close()
        except Exception:
            pass


def _server_status():
    """探测服务端连接与 Key 有效性。"""
    url = config.PROXY_SERVER_URL
    if not url:
        return {"status": "unconfigured", "message": "未配置 PROXY_SERVER_URL，请在 .env 中填写服务商地址。"}
    import requests
    try:
        if config.PROXY_API_KEY:
            r = requests.post(url, headers={"X-API-Key": config.PROXY_API_KEY}, json={}, timeout=10)
        else:
            r = requests.post(url, json={}, timeout=10)
        if r.status_code == 401:
            return {"status": "invalid_key", "message": f"服务端在线，但 Key 无效或已过期（HTTP 401）。"}
        return {"status": "ok", "message": f"服务端在线，Key 有效（HTTP {r.status_code}）。"}
    except Exception as e:
        return {"status": "offline", "message": f"无法连接服务端: {type(e).__name__}: {e}"}



mcp = FastMCP("xhs-sender")


@mcp.tool()
def xhs_send_next() -> dict:
    """自动发送一条私信：从设备列表领取一个可用发送设备，再领取一个接收方，调用服务端执行发送。返回执行结果。"""
    return _run_scheduler_once()


@mcp.tool()
def xhs_list_devices() -> dict:
    """列出本机 MongoDB 中配置的全部发送设备（昵称/用户ID/备注）。"""
    try:
        client = _mongo_client()
        db = client[config.MONGO_DB_NAME]
        coll = db[config.MONGO_DEVICE_COLLECTION]
        devices = list(coll.find({}, {"nickname": 1, "userid": 1, "remarks": 1}).limit(100))
        result = [
            {
                "userid": d.get("userid", ""),
                "nickname": d.get("nickname", ""),
                "remarks": d.get("remarks", ""),
            }
            for d in devices
        ]
        client.close()
        return {"status": "ok", "count": len(result), "devices": result}
    except Exception as e:
        return {"status": "error", "message": f"查询设备失败: {type(e).__name__}: {e}"}


@mcp.tool()
def xhs_server_status() -> dict:
    """查看服务端连接状态与当前 Key 是否有效。"""
    return _server_status()


@mcp.tool()
def xhs_add_receiver(receiver_id: str) -> dict:
    """将一个接收方 userid 加入待发送队列（写入 userid 集合），后续由 xhs_send_next 调度发送。"""
    if not receiver_id or not receiver_id.strip():
        return {"status": "error", "message": "receiver_id 不能为空。"}
    receiver_id = receiver_id.strip()
    try:
        client = _mongo_client()
        db = client[config.MONGO_DB_NAME]
        coll = db[config.MONGO_USER_ID_COLLECTION]
        existed = coll.find_one({"user_id": receiver_id})
        if existed:
            client.close()
            return {"status": "ok", "message": f"接收方 {receiver_id} 已在队列中。"}
        coll.insert_one({"user_id": receiver_id})
        client.close()
        return {"status": "ok", "message": f"接收方 {receiver_id} 已加入待发送队列。"}
    except Exception as e:
        return {"status": "error", "message": f"添加接收方失败: {type(e).__name__}: {e}"}


if __name__ == "__main__":
    logger.info(f"MCP Server 启动，监听 0.0.0.0:8090 (streamable-http)")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8090)
