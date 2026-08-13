from pymongo import MongoClient
from pymongo.collection import Collection
import config
_client = None

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
    client = get_mongo_client()
    db = client[config.MONGO_DB_NAME]
    return db[collection_name]

def get_devices_collection() -> Collection:
    """
    获取设备集合的 Collection 对象。
    从 config.py 读取要使用的集合名称。
    """
    return get_collection(config.MONGO_DEVICE_COLLECTION)