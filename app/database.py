from pymongo import MongoClient
import config

def connect_to_mongo():
    try:
        client = MongoClient(f'mongodb://{config.MONGO_HOST}:{config.MONGO_PORT}/', username=config.MONGO_USERNAME, password=config.MONGO_PASSWORD, authSource=config.MONGO_AUTH_SOURCE, serverSelectionTimeoutMS=5000)
        db = client[config.MONGO_DB_NAME]
        client.server_info()
        return client, db
    except Exception as e:
        raise ConnectionError(f"无法连接到MongoDB: {e}")

def close_mongo_connection(client):
    if client:
        client.close()
