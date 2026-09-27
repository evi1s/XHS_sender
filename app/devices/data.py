import importlib
import os
import threading
from pymongo import MongoClient
from pymongo.collection import Collection
import config
_client = None
_config_mtime = None
_config_lock = threading.Lock()


def _reload_config_if_changed():
    """在“软件设置”改写 config.py 后，重新加载内存中的 config 模块，
    使新的集合名 / 数据库名无需重启软件即可即时生效（否则集合名会一直用启动时的旧值）。"""
    global _config_mtime
    try:
        path = os.path.abspath(getattr(config, '__file__', 'config.py'))
        mtime = os.path.getmtime(path)
    except OSError:
        return
    if _config_mtime == mtime:
        return
    with _config_lock:
        if _config_mtime == mtime:
            return
        importlib.reload(config)
        _config_mtime = mtime


def get_mongo_client() -> MongoClient:
    """
    获取一个全局的MongoDB客户端实例。
    使用从配置文件导入的配置。
    """
    global _client
    if _client is None:
        uri = (
            f"mongodb://{config.MONGO_USERNAME}:{config.MONGO_PASSWORD}@"
            f"{config.MONGO_HOST}:{config.MONGO_PORT}/{config.MONGO_DB_NAME}"
            f"?authSource={config.MONGO_AUTH_SOURCE}"
        )
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return _client

def get_collection(collection_name: str) -> Collection:
    """
    获取指定名称的 Collection 对象。
    """
    _reload_config_if_changed()
    client = get_mongo_client()
    db = client[config.MONGO_DB_NAME]
    return db[collection_name]

def get_devices_collection() -> Collection:
    """
    获取设备集合的 Collection 对象。
    从 config.py 读取要使用的集合名称（调用前先刷新 config，确保设置改动即时生效）。
    """
    _reload_config_if_changed()
    return get_collection(config.MONGO_DEVICE_COLLECTION)
