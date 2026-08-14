
import os
import json
import random
import time
from nicegui import ui

DEFAULT_SOCKS5_PROXY = {
    'host': '127.0.0.1',
    'port': 1080,
    'username': '',
    'password': '',
    'enabled': False,
}

socks5_config = DEFAULT_SOCKS5_PROXY.copy()


def load_socks5_config():
    global socks5_config
    config_file = 'socks5_config.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                socks5_config.update(json.load(f))
        except Exception as e:
            print(f'读取socks5配置文件失败: {e}')
    return socks5_config


def save_socks5_config():
    config_file = 'socks5_config.json'
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(socks5_config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'保存socks5配置文件失败: {e}')


def create_socks5_config_ui():
    """
    创建 SOCKS5 代理配置页面。
    """
    load_socks5_config()

    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-indigo-600 to-purple-600 rounded-t-2xl px-4 py-3'):
            ui.icon('vpn_key', size='28px').classes('text-white')
            ui.label('SOCKS5 代理配置').classes('text-xl font-bold text-white')

        with ui.column().classes('w-full gap-2 px-6 py-4'):
            with ui.card().classes('w-full gap-2 p-4'):
                ui.label('启用 SOCKS5').classes('text-sm font-semibold text-indigo-600')
                socks5_enabled = ui.switch('启用代理', value=socks5_config.get('enabled', False)).classes('mt-1')
                ui.label('代理服务器地址').classes('text-sm font-semibold text-indigo-600 mt-2')
                socks5_host = ui.input('主机', value=socks5_config.get('host', '127.0.0.1')).props('outlined').classes('w-full')
                ui.label('代理端口').classes('text-sm font-semibold text-indigo-600 mt-2')
                socks5_port = ui.input('端口', value=str(socks5_config.get('port', 1080))).props('outlined').classes('w-full')
                ui.label('代理用户名（可选）').classes('text-sm font-semibold text-indigo-600 mt-2')
                socks5_username = ui.input('用户名', value=socks5_config.get('username', '')).props('outlined').classes('w-full')
                ui.label('代理密码（可选）').classes('text-sm font-semibold text-indigo-600 mt-2')
                socks5_password = ui.input('密码', value=socks5_config.get('password', ''), password=True).props('outlined').classes('w-full')

            def save_socks5():
                socks5_config.update({
                    'enabled': socks5_enabled.value,
                    'host': socks5_host.value,
                    'port': int(socks5_port.value or 1080),
                    'username': socks5_username.value,
                    'password': socks5_password.value,
                })
                save_socks5_config()
                ui.notify('SOCKS5 配置已保存', type='positive')

            with ui.row().classes('w-full justify-center gap-4 mt-4'):
                ui.button('保存配置', on_click=save_socks5).props('color=primary').classes('px-8')
                ui.button('重新加载', on_click=lambda: (load_socks5_config(), ui.notify('配置已重新加载', type='info'))).props('color=secondary').classes('px-8')
