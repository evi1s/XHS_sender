import sys
import datetime
from pymongo import MongoClient, ReturnDocument
import config
from loguru import logger


class DeviceManager:
    def __init__(self):
        try:
            self.client = MongoClient(f'mongodb://{config.MONGO_HOST}:{config.MONGO_PORT}/', username=config.MONGO_USERNAME, password=config.MONGO_PASSWORD, authSource=config.MONGO_AUTH_SOURCE, serverSelectionTimeoutMS=5000)
            self.db = self.client[config.MONGO_DB_NAME]
            self.collection = self.db[config.MONGO_DEVICE_COLLECTION]
            self.client.server_info()
            logger.info(f"DeviceManager: 成功连接到MongoDB，目标工作集合: '{config.MONGO_DEVICE_COLLECTION}'。")
        except Exception as e:
            logger.critical(f"DeviceManager: 无法连接到MongoDB。错误: {e}")
            sys.exit(1)

    def get_device_by_userid(self, userid):
        doc = self.collection.find_one({'userid': userid})
        if doc and '_id' in doc:
            doc.pop('_id')
        return doc

    def find_available_user_and_claim(self, claim_duration_seconds):
        now_time = datetime.datetime.now()
        now_str = now_time.strftime('%Y-%m-%d %H:%M:%S')
        today_str = now_time.strftime('%Y-%m-%d')
        claim_until_time = now_time + datetime.timedelta(seconds=claim_duration_seconds)
        claim_until_str = claim_until_time.strftime('%Y-%m-%d %H:%M:%S')
        query = {
            '$and': [
                {'$or': [{'next_send_time': {'$exists': False}}, {'next_send_time': {'$lte': now_str}}]},
                {'$or': [{'last_usage_date': {'$ne': today_str}}, {'daily_usage_count': {'$lt': config.MAX_DAILY_USAGE}}]}
            ]
        }
        update = {'$set': {'next_send_time': claim_until_str}}
        doc = self.collection.find_one_and_update(query, update, sort=[('next_send_time', 1)], return_document=ReturnDocument.AFTER)
        if doc and '_id' in doc:
            doc.pop('_id')
        return doc

    def increment_daily_usage(self, userid):
        now = datetime.datetime.now()
        today_str = now.strftime('%Y-%m-%d')
        user_doc = self.collection.find_one({'userid': userid})
        if user_doc:
            if user_doc.get('last_usage_date') == today_str:
                self.collection.update_one({'userid': userid}, {'$inc': {'daily_usage_count': 1}})
            else:
                self.collection.update_one({'userid': userid}, {'$set': {'daily_usage_count': 1, 'last_usage_date': today_str}})

    def update_next_send_time(self, userid, next_send_timestamp):
        next_send_datetime = datetime.datetime.fromtimestamp(next_send_timestamp)
        next_send_time_str = next_send_datetime.strftime('%Y-%m-%d %H:%M:%S')
        self.collection.update_one({'userid': userid}, {'$set': {'next_send_time': next_send_time_str}})

    def record_consecutive_failure(self, userid):
        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
        user_doc = self.collection.find_one({'userid': userid})
        if not user_doc:
            return 1, False
        last_fail_date = user_doc.get('last_fail_date', '')
        consecutive_fail_days = user_doc.get('consecutive_fail_days', 0)
        crossed_day = False
        if last_fail_date == today_str:
            consecutive_fail_days += 1
        elif last_fail_date:
            try:
                if (datetime.datetime.strptime(today_str, '%Y-%m-%d') - datetime.datetime.strptime(last_fail_date, '%Y-%m-%d')).days == 1:
                    consecutive_fail_days += 1
                    crossed_day = True
                else:
                    consecutive_fail_days = 1
            except:
                consecutive_fail_days = 1
        else:
            consecutive_fail_days = 1
        self.collection.update_one({'userid': userid}, {'$set': {'last_fail_date': today_str, 'consecutive_fail_days': consecutive_fail_days}})
        return consecutive_fail_days, crossed_day

    def clear_consecutive_failure(self, userid):
        self.collection.update_one({'userid': userid}, {'$set': {'consecutive_fail_days': 0, 'last_fail_date': ''}})

    def close(self):
        self.client.close()
