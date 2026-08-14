from nicegui import ui
import config
import asyncio
from database import connect_to_mongo, close_mongo_connection
from devices.data import get_devices_collection, get_collection
from loguru import logger
import sys


def create_ui():
    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-indigo-600 to-purple-600 rounded-t-2xl px-4 py-3'):
            ui.icon('settings', size='28px').classes('text-white')
            ui.label('软件设置').classes('text-xl font-bold text-white')
            ui.space()
        with ui.column().classes('w-full gap-4 px-4 py-4'):
            ui.label('配置参数说明').classes('text-sm text-gray-500')
            with ui.row().classes('w-full gap-4'):
                with ui.column().classes('gap-2 flex-1'):
                    ui.label('数据库设置').classes('text-lg font-semibold')
                    inputs = {}
                    inputs['MONGO_HOST'] = ui.input('MongoDB主机', value=config.MONGO_HOST).props('outlined').classes('w-full')
                    inputs['MONGO_PORT'] = ui.input('MongoDB端口', value=str(config.MONGO_PORT)).props('outlined').classes('w-full')
                    inputs['MONGO_USERNAME'] = ui.input('MongoDB用户名', value=config.MONGO_USERNAME).props('outlined').classes('w-full')
                    inputs['MONGO_PASSWORD'] = ui.input('MongoDB密码', value=config.MONGO_PASSWORD).props('outlined').classes('w-full')
                    inputs['MONGO_AUTH_SOURCE'] = ui.input('认证源', value=config.MONGO_AUTH_SOURCE).props('outlined').classes('w-full')
                with ui.column().classes('gap-2 flex-1'):
                    ui.label('任务与连接参数').classes('text-lg font-semibold')
                    inputs['SUCCESS_SEND_INTERVAL'] = ui.input('成功发送间隔(秒)', value=str(config.SUCCESS_SEND_INTERVAL)).props('outlined').classes('w-full')
                    inputs['MAX_RETRY_ATTEMPTS'] = ui.input('最大重试次数', value=str(config.MAX_RETRY_ATTEMPTS)).props('outlined').classes('w-full')
                    inputs['MAX_DAILY_USAGE'] = ui.input('每日最大使用量', value=str(config.MAX_DAILY_USAGE)).props('outlined').classes('w-full')
                    inputs['TASK_INTERVAL'] = ui.input('任务间隔(秒)', value=str(config.TASK_INTERVAL)).props('outlined').classes('w-full')
                    inputs['USER_POLLING_INTERVAL'] = ui.input('轮询间隔(秒)', value=str(config.USER_POLLING_INTERVAL)).props('outlined').classes('w-full')
            with ui.row().classes('w-full gap-4'):
                with ui.column().classes('gap-2 flex-1'):
                    ui.label('数据库集合设置').classes('text-lg font-semibold')
                    inputs['MONGO_DB_NAME'] = ui.input('数据库名称', value=config.MONGO_DB_NAME).props('outlined').classes('w-full')
                    inputs['MONGO_DEVICE_COLLECTION'] = ui.input('设备集合', value=config.MONGO_DEVICE_COLLECTION).props('outlined').classes('w-full')
                    inputs['MONGO_USER_ID_COLLECTION'] = ui.input('UserID集合', value=config.MONGO_USER_ID_COLLECTION).props('outlined').classes('w-full')
                    inputs['MONGO_SEND_TEXT_COLLECTION'] = ui.input('发送文本集合', value=config.MONGO_SEND_TEXT_COLLECTION).props('outlined').classes('w-full')
                    inputs['MONGO_CHECK_STATUS_COLLECTION'] = ui.input('状态码检测集合', value=config.MONGO_CHECK_STATUS_COLLECTION).props('outlined').classes('w-full')

            async def save_config():
                import importlib
                import os
                cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                for key, element in inputs.items():
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if stripped.startswith(key) and not stripped.startswith('#'):
                            val = element.value
                            if key in ('MONGO_PORT', 'SUCCESS_SEND_INTERVAL', 'MAX_RETRY_ATTEMPTS', 'MAX_DAILY_USAGE', 'TASK_INTERVAL', 'USER_POLLING_INTERVAL'):
                                lines[i] = f"{key} = int(os.getenv('{key}', '{val}'))\n"
                            else:
                                lines[i] = f"{key} = os.getenv('{key}', '{val}')\n"
                            break
                with open(cfg_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                importlib.reload(config)
                ui.notify('配置已保存并生效！', color='positive')

            async def load_config():
                import importlib
                importlib.reload(config)
                for key, element in inputs.items():
                    val = getattr(config, key, '')
                    element.value = str(val)
                ui.notify('配置已重新加载！', color='info')

            with ui.row().classes('w-full justify-center gap-4 mt-4'):
                ui.button('保存所有配置', on_click=save_config, icon='save', color='primary').classes('px-8')
                ui.button('重新加载配置', on_click=load_config, icon='refresh', color='secondary').classes('px-8')
