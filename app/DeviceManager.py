
from pymongo import MongoClient
from loguru import logger

class DeviceManager:
    """
    负责从 MongoDB 管理和获取设备配置信息。
    """
    def __init__(self, mongo_host, mongo_port, mongo_username, mongo_password, mongo_db_name, device_collection_name='devices'):
        self.mongo_host = mongo_host
        self.mongo_port = mongo_port
        self.mongo_username = mongo_username
        self.mongo_password = mongo_password
        self.mongo_db_name = mongo_db_name
        self.device_collection_name = device_collection_name
        self._client = None
        self._db = None
        self._collection = None

    def _connect(self):
        """
        建立或验证与 MongoDB 的连接。
        """
        if self._client is None:
            try:
                self._client = MongoClient(
                    f'mongodb://{self.mongo_host}:{self.mongo_port}/',
                    username=self.mongo_username,
                    password=self.mongo_password,
                    authSource='admin'
                )
                self._client.admin.command('ping')
                self._db = self._client[self.mongo_db_name]
                self._collection = self._db[self.device_collection_name]
                logger.info("DeviceManager: 成功连接到MongoDB。")
            except Exception as e:
                logger.error(f"DeviceManager: 连接到MongoDB失败: {e}")
                self._client = None
                raise
        elif not self._client.admin.command('ping'):
            logger.warning("DeviceManager: MongoDB 连接已断开，尝试重新连接...")
            self._client = None
            self._connect()

    def get_device_by_userid(self, userid):
        """
        根据 userid 从 MongoDB 获取设备配置。

        :param userid: 要查询的用户的 ID。
        :return: 设备配置字典，如果没有找到则返回 None。
        """
        try:
            self._connect()
            logger.info(f"DeviceManager: 正在为用户ID '{userid}' 获取设备配置...")
            device_config = self._collection.find_one({'userid': userid})
            if device_config:
                if '_id' in device_config:
                    del device_config['_id']
                logger.info(f"DeviceManager: 找到用户ID '{userid}' 的设备配置。")
                return device_config
            else:
                logger.warning(f"DeviceManager: 未找到用户ID '{userid}' 的设备配置。")
                return None
        except Exception as e:
            logger.error(f"DeviceManager: 获取用户ID '{userid}' 的设备配置时发生错误: {e}")
            return None

    def close(self):
        """
        关闭 MongoDB 连接。
        """
        if self._client:
            self._client.close()
            logger.info("DeviceManager: MongoDB 连接已关闭。")
