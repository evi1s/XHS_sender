import re
import os
from nicegui import ui

CONFIG_FILE = 'config.py'


def create_ui():
    """服务器连接与 API Key 设置"""

    def load_config():
        config = {}
        if not os.path.exists(CONFIG_FILE):
            return

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    match = re.match(r'^\s*([A-Z_]+)\s*=\s*"(.*?)"\s*$', line)
                    if match:
                        key, value = match.groups()
                        config[key] = value

            if 'PROXY_SERVER_URL' in config:
                proxy_url_input.set_value(config['PROXY_SERVER_URL'])
            if 'PROXY_API_KEY' in config:
                proxy_key_input.set_value(config['PROXY_API_KEY'])

        except Exception as e:
            ui.notify(f'加载配置文件失败: {e}', color='negative')

    async def save_config():
        url = proxy_url_input.value
        api_key = proxy_key_input.value

        lines = []
        url_found = False
        key_found = False

        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        for i, line in enumerate(lines):
            if re.match(r'^\s*PROXY_SERVER_URL\s*=', line):
                lines[i] = f'PROXY_SERVER_URL = "{url}"\n'
                url_found = True
            elif re.match(r'^\s*PROXY_API_KEY\s*=', line):
                lines[i] = f'PROXY_API_KEY = "{api_key}"\n'
                key_found = True

        if not url_found:
            lines.append(f'PROXY_SERVER_URL = "{url}"\n')
        if not key_found:
            lines.append(f'PROXY_API_KEY = "{api_key}"\n')

        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            ui.notify('配置已保存', color='positive')
        except Exception as e:
            ui.notify(f'保存配置失败: {e}', color='negative')

    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-violet-600 to-purple-600 rounded-t-2xl px-4 py-3'):
            ui.icon('vpn_key', size='28px').classes('text-white')
            ui.label('授权设置').classes('text-xl font-bold text-white')

        with ui.column().classes('w-full gap-4 px-4 py-4'):
            ui.label('配置服务端地址与 API Key，此设置将保存到应用配置文件中。').classes('text-sm text-gray-500')

            proxy_url_input = ui.input(
                label='Server_URL',
                placeholder='例如: http://127.0.0.1:8000/execute-task'
            ).props('outlined').classes('w-full')

            proxy_key_input = ui.input(
                label='API_Key',
                placeholder='例如: YOUR-SECRET-API-KEY-FOR-CLIENTS-12345'
            ).props('outlined').classes('w-full')

            ui.button('保存配置', on_click=save_config, icon='save', color='primary').classes('w-full mt-2')

    ui.timer(0.1, load_config, once=True)
