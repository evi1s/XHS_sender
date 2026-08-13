import time
import datetime
import random
import string
import requests
import json
import sys
import os
from pymongo import MongoClient, ReturnDocument
from loguru import logger
import config

log_dir = "log_client"
os.makedirs(log_dir, exist_ok=True)
logger.remove()
def custom_stdout_sink(message): sys.stdout.write(message); sys.stdout.flush()
logger.add(custom_stdout_sink, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>| <level>{level: <8}</level>| <level>{message}</level>", colorize=True)


class DeviceManager:
    def __init__(self):
        try:
            self.client = MongoClient(f'mongodb://{config.MONGO_HOST}:{config.MONGO_PORT}/', username=config.MONGO_USERNAME, password=config.MONGO_PASSWORD, authSource=config.MONGO_AUTH_SOURCE, serverSelectionTimeoutMS=5000)
            self.db = self.client[config.MONGO_DB_NAME]; self.collection = self.db[config.MONGO_DEVICE_COLLECTION]; self.client.server_info()
            logger.info(f"DeviceManager: 成功连接到MongoDB，目标工作集合: '{config.MONGO_DEVICE_COLLECTION}'。")
        except Exception as e: logger.critical(f"DeviceManager: 无法连接到MongoDB。错误: {e}"); sys.exit(1)
    def get_device_by_userid(self, userid): doc = self.collection.find_one({'userid': userid}); (doc and '_id' in doc) and doc.pop('_id'); return doc
    def find_available_user_and_claim(self, claim_duration_seconds):
        now_time = datetime.datetime.now(); now_str = now_time.strftime('%Y-%m-%d %H:%M:%S'); today_str = now_time.strftime('%Y-%m-%d'); claim_until_time = now_time + datetime.timedelta(seconds=claim_duration_seconds); claim_until_str = claim_until_time.strftime('%Y-%m-%d %H:%M:%S')
        query = {'$and': [{'$or': [{'next_send_time': {'$exists': False}}, {'next_send_time': {'$lte': now_str}}]}, {'$or': [{'last_usage_date': {'$ne': today_str}}, {'daily_usage_count': {'$lt': config.MAX_DAILY_USAGE}}]}]}
        update = {'$set': {'next_send_time': claim_until_str}}
        doc = self.collection.find_one_and_update(query, update, sort=[('next_send_time', 1)], return_document=ReturnDocument.AFTER); (doc and '_id' in doc) and doc.pop('_id'); return doc
    def increment_daily_usage(self, userid):
        now = datetime.datetime.now(); today_str = now.strftime('%Y-%m-%d'); user_doc = self.collection.find_one({'userid': userid})
        if user_doc:
            if user_doc.get('last_usage_date') == today_str: self.collection.update_one({'userid': userid}, {'$inc': {'daily_usage_count': 1}})
            else: self.collection.update_one({'userid': userid}, {'$set': {'daily_usage_count': 1, 'last_usage_date': today_str}})
    def update_next_send_time(self, userid, next_send_timestamp): next_send_datetime = datetime.datetime.fromtimestamp(next_send_timestamp); next_send_time_str = next_send_datetime.strftime('%Y-%m-%d %H:%M:%S'); self.collection.update_one({'userid': userid}, {'$set': {'next_send_time': next_send_time_str}})
    def record_consecutive_failure(self, userid):
        today_str = datetime.datetime.now().strftime('%Y-%m-%d'); user_doc = self.collection.find_one({'userid': userid});
        if not user_doc: return 1
        last_fail_date = user_doc.get('last_fail_date', ''); consecutive_fail_days = user_doc.get('consecutive_fail_days', 0)
        if last_fail_date == today_str: return consecutive_fail_days
        if last_fail_date:
            try:
                if (datetime.datetime.strptime(today_str, '%Y-%m-%d') - datetime.datetime.strptime(last_fail_date, '%Y-%m-%d')).days == 1: consecutive_fail_days += 1
                else: consecutive_fail_days = 1
            except: consecutive_fail_days = 1
        else: consecutive_fail_days = 1
        self.collection.update_one({'userid': userid}, {'$set': {'last_fail_date': today_str, 'consecutive_fail_days': consecutive_fail_days}}); return consecutive_fail_days
    def clear_consecutive_failure(self, userid): self.collection.update_one({'userid': userid}, {'$set': {'consecutive_fail_days': 0, 'last_fail_date': ''}})
    def close(self): self.client.close()

def call_remote_proxy(payload: dict) -> (bool, dict):
    """
    调用远程执行任务，并以流式方式处理SSE响应。
    """
    logger.info("准备调用远程服务器执行任务 (SSE模式)...")
    headers = {"X-API-Key": config.PROXY_API_KEY, "Content-Type": "application/json"}
    final_status_data = None
    
    try:
        with requests.post(config.PROXY_SERVER_URL, headers=headers, json=payload, timeout=300, stream=True) as response:
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data:'):
                        try:
                            data_str = line_str[5:].strip()
                            if not data_str: continue

                            data = json.loads(data_str)
                            
                            if 'log' in data:
                                logger.info(f"[SERVER] {data['log']}")
                            elif 'status' in data:
                                final_status_data = data
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"无法解析服务器发送的事件流: {line_str}")

            if final_status_data and final_status_data.get('status') == 'success':
                 logger.success(f"远程服务器报告任务成功: {final_status_data.get('message')}")
                 return True, final_status_data
            else:
                 reason = final_status_data.get('reason') if final_status_data else "未收到明确的成功或失败状态。"
                 logger.error(f"远程服务器报告任务失败: {reason}")
                 return False, final_status_data

    except requests.exceptions.HTTPError as e:
        logger.error(f"远程服务器HTTP错误: 状态码 {e.response.status_code}, 原因: {e.response.text}")
        return False, {"status": "error", "reason": f"远程服务器HTTP错误: {e.response.text}"}
    except requests.exceptions.RequestException as e:
        logger.error(f"无法连接到服务器或连接中断: {e}")
        return False, {"status": "error", "reason": f"网络或连接错误: {e}"}

STALE_CLAIM_MINUTES = 30  # 孤儿领取（进程异常退出）超过该时长后自动重新可领取

NETWORK_ERROR_KEYWORDS = (
    "网络或连接错误", "客户端连接关闭", "获取IP失败", "无法连接到服务器",
    "连接中断", "网络连接失败", "连接超时", "连接失败",
    "ConnectionError", "Connection", "ProxyError", "timeout", "超时",
)


AUTH_ERROR_KEYWORDS = (
    "无效的 api key", "缺少 api key", "套餐已过期", "次数已用完",
    "客户已被暂停",
)

class NetworkRetryAbortError(Exception):
    """网络/连接类错误（含"获取小红书IP失败"）：立即终止重试，由外层统一退回接收方。"""
    pass

def _is_network_error(reason) -> bool:
    """判断远程返回的失败原因是否为网络/连接类（非业务）错误。"""
    if not reason:
        return False
    r = str(reason).lower()
    return any(k.lower() in r for k in NETWORK_ERROR_KEYWORDS)

def _is_auth_error(reason) -> bool:
    """判断远程返回的失败原因是否为确定性鉴权/计费错误（key无效/套餐过期/次数用完等）。"""
    if not reason:
        return False
    r = str(reason).lower()
    return any(k in r for k in AUTH_ERROR_KEYWORDS)


def _claim_receiver(user_id_collection):
    """标记式领取一个接收方：文档保留在集合中，仅打上 claimed 标记。

    相比 find_one_and_delete，即使进程异常退出，userid 也不会丢失；
    超过 STALE_CLAIM_MINUTES 的孤儿领取会自动重新可领取。
    """
    stale_before = datetime.datetime.now() - datetime.timedelta(minutes=STALE_CLAIM_MINUTES)
    return user_id_collection.find_one_and_update(
        {'$or': [
            {'claimed': {'$ne': True}},
            {'claim_time': {'$lt': stale_before}},
        ]},
        {'$set': {'claimed': True, 'claim_time': datetime.datetime.now()}},
        sort=[('_id', 1)],
        return_document=ReturnDocument.AFTER,
    )


def _release_receiver(user_id_collection, receiver_doc):
    """将接收方退回 MongoDB（清除领取标记），userid 不丢失。"""
    if not receiver_doc:
        return False
    result = user_id_collection.update_one(
        {'_id': receiver_doc['_id']},
        {'$set': {'claimed': False, 'claim_time': None}},
    )
    return result.modified_count > 0


def client_main_task(sender_device_config, check_user_device_config, db_collections, device_manager_instance):
    userid = sender_device_config['userid']; user_id_collection = db_collections['user_id']; receiver_doc = None; task_completed = False
    try:
        for _ in range(config.MAX_RETRY_ATTEMPTS):
            receiver_doc = _claim_receiver(user_id_collection)
            if receiver_doc: break
            logger.warning(f"未能从集合'{config.MONGO_USER_ID_COLLECTION}'获取接收方，等待 {config.USER_ID_POLLING_INTERVAL}秒后重试..."); time.sleep(config.USER_ID_POLLING_INTERVAL)
        if not receiver_doc: raise ValueError(f"在尝试 {config.MAX_RETRY_ATTEMPTS} 次后仍未能获取到接收方。")
        receiver_id = receiver_doc['user_id']; logger.success(f"[{userid}] 成功获取接收方: {receiver_id}")
        last_exception = None
        for attempt in range(config.MAX_RETRY_ATTEMPTS):
            try:
                message_text = None; card_template = None;
                if config.MESSAGE_SEND_MODE in [config.SEND_MODE_TEXT_ONLY, config.SEND_MODE_CARD_AND_TEXT]: message_text = db_collections['send_text'].aggregate([{'$sample': {'size': 1}}]).next()['text']
                if config.MESSAGE_SEND_MODE in [config.SEND_MODE_CARD_ONLY, config.SEND_MODE_CARD_AND_TEXT]:
                    card_json_path = 'xhs3.json'
                    if os.path.exists(card_json_path):
                        try:
                            with open(card_json_path, 'r', encoding='utf-8') as f: card_template = json.load(f)
                            logger.info(f"成功从本地文件 '{card_json_path}' 加载卡片模板。")
                        except Exception as e: logger.error(f"加载卡片模板文件 '{card_json_path}' 失败: {e}，本次私信不发送卡片。")
                    else: logger.warning(f"卡片模板文件 '{card_json_path}' 不存在，本次私信将不发送卡片。")
                if not message_text and not card_template: raise ValueError("消息内容和卡片模板均为空，请检查配置或文件。")
                payload = {"sender_device_config": sender_device_config, "check_user_device_config": check_user_device_config, "receiver_id": receiver_id, "message_text": message_text, "card_template": card_template}
                
                success, response_data = call_remote_proxy(payload)
                
                if success:
                    user_id_collection.delete_one({'_id': receiver_doc['_id']})
                    task_completed = True
                    device_manager_instance.increment_daily_usage(userid); device_manager_instance.update_next_send_time(userid, time.time() + config.SUCCESS_SEND_INTERVAL); device_manager_instance.clear_consecutive_failure(userid)
                    logger.success(f"[{userid}] 本次任务完成，该账号状态已更新。"); return
                else:
                    reason = response_data.get('reason') if response_data else "未知远程错误"
                    if _is_network_error(reason):
                        raise NetworkRetryAbortError(f"网络或连接错误，终止重试并退回接收方: {reason}")
                    if _is_auth_error(reason):
                        raise NetworkRetryAbortError(f"鉴权或套餐错误，终止重试并退回接收方: {reason}")
                    last_exception = Exception(f"远程报告错误 (第 {attempt + 1} 次尝试): {reason}")
                    logger.warning(f"任务尝试失败 (第 {attempt + 1}/{config.MAX_RETRY_ATTEMPTS} 次)，5秒后重试...")
                    time.sleep(5)
            except NetworkRetryAbortError:
                raise
            except Exception as e: 
                last_exception = e
                logger.error(f"任务期间发生本地异常 (第 {attempt + 1}/{config.MAX_RETRY_ATTEMPTS} 次): {e}"); 
                time.sleep(5)
        raise last_exception
    except Exception as final_exception:
        if receiver_doc and not task_completed:
            _release_receiver(user_id_collection, receiver_doc)
            logger.warning(f"[{userid}] 已将接收方 {receiver_doc.get('user_id')} 的信息回滚（重新入队，userid 未丢失）。")
        raise final_exception


if __name__ == '__main__':
    log_filename_suffix = sys.argv[1] if len(sys.argv) > 1 else "scheduler"; log_filepath = os.path.join(log_dir, f"client-{log_filename_suffix}.log"); logger.add(log_filepath, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss}|{level}|{message}", rotation="10 MB", encoding='utf-8')
    
    device_manager = DeviceManager()

    checker_config = device_manager.get_device_by_userid(config.CHECK_USER_ID)
    
    if not checker_config:
        logger.critical(f"错误：无法在集合 '{config.MONGO_DEVICE_COLLECTION}' 中找到主账号 '{config.CHECK_USER_ID}'。")
        device_manager.close()
        sys.exit(1)

    logger.success(f"成功从 '{config.MONGO_DEVICE_COLLECTION}' 加载主账号。")

    if len(sys.argv) > 1:
        pass
    else:
        print("--> [客户端-自动调度模式] 启动...")
        try:
            while True:
                claimed_user = device_manager.find_available_user_and_claim(config.USER_POLLING_INTERVAL + 120)
                if claimed_user:
                    userid = claimed_user['userid']
                    logger.success(f"找到可用账号 {userid}，开始执行任务...")
                    mongo_client = None
                    try:
                        mongo_client = MongoClient(f'mongodb://{config.MONGO_HOST}:{config.MONGO_PORT}/', username=config.MONGO_USERNAME, password=config.MONGO_PASSWORD, authSource=config.MONGO_AUTH_SOURCE)
                        db = mongo_client[config.MONGO_DB_NAME]
                        db_collections = {"user_id": db[config.MONGO_USER_ID_COLLECTION], "send_text": db[config.MONGO_SEND_TEXT_COLLECTION], "comment": db[config.MONGO_COMMENT_COLLECTION]}
                        
                        client_main_task(claimed_user, checker_config, db_collections, device_manager)

                    except Exception as e:
                        logger.error(f"判定任务最终对 {userid} 失败: {e}")
                        consecutive_days = device_manager.record_consecutive_failure(userid)
                        if consecutive_days >= 2:
                            logger.error(f"[{userid}] 已连续 {consecutive_days} 天失败，进入长时冷却。")
                            device_manager.update_next_send_time(userid, time.time() + config.FAILURE_COOLDOWN_30_DAYS)
                        else:
                            logger.error(f"[{userid}] 任务失败（第 {consecutive_days} 天），将冷却24小时。")
                            device_manager.update_next_send_time(userid, time.time() + config.FAILURE_COOLDOWN_INTERVAL)
                    finally:
                        if mongo_client: mongo_client.close()

                    if hasattr(config, 'TASK_INTERVAL') and config.TASK_INTERVAL > 0:
                        logger.info(f"本次发送任务已结束，等待 {config.TASK_INTERVAL} 秒后调度下一个任务...")
                        time.sleep(config.TASK_INTERVAL)

                else:
                    logger.info(f"无可用账号，将在 {config.USER_POLLING_INTERVAL} 秒后轮询...")
                    time.sleep(config.USER_POLLING_INTERVAL)
        except KeyboardInterrupt:
            logger.warning("捕获到(Ctrl+C)，正在准备退出...")
        finally:
            logger.info("正在关闭 DeviceManager 连接...")
            device_manager.close()
