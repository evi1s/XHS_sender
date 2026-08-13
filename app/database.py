import motor.motor_asyncio
from config import (
    MONGO_HOST, MONGO_PORT, MONGO_USERNAME, MONGO_PASSWORD, 
    MONGO_AUTH_SOURCE, MONGO_DB_NAME
)

class Database:
    """
    用于管理和提供 MongoDB 异步客户端的单例类。
    """
    _client = None

    @classmethod
    def get_client(cls):
        """获取异步MongoDB客户端单例。"""
        if cls._client is None:
            cls._client = motor.motor_asyncio.AsyncIOMotorClient(
                host=MONGO_HOST,
                port=MONGO_PORT,
                username=MONGO_USERNAME,
                password=MONGO_PASSWORD,
                authSource=MONGO_AUTH_SOURCE,
                serverSelectionTimeoutMS=5000 
            )
        return cls._client

    @classmethod
    def get_db(cls):
        """获取应用的主数据库。"""
        client = cls.get_client()
        return client[MONGO_DB_NAME]

db = Database.get_db()

async def connect_to_mongo():
    """
    在应用启动时验证数据库连接。
    """
    try:
        client = Database.get_client()
        await client.admin.command('ping')
    except Exception as e:
        raise e

def close_mongo_connection():
    """
    在应用关闭时关闭MongoDB连接。
    """
    if Database._client:
        Database._client.close()