from pymongo import MongoClient
from pymongo.collection import Collection
import config

_client = None


def get_mongo_client() -> MongoClient:
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
    client = get_mongo_client()
    db = client[config.MONGO_DB_NAME]
    return db[collection_name]


def get_devices_collection() -> Collection:
    return get_collection(config.MONGO_DEVICE_COLLECTION)
