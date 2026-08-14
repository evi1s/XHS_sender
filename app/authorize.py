import importlib
from nicegui import ui
import config


def mask_key(key: str) -> str:
    if not key:
        return ''
    if len(key) <= 8:
        return '*' * len(key)
    return key[:4] + '*' * (len(key) - 8) + key[-4:]


def create_ui():
    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-violet-600 to-purple-700 rounded-t-2xl px-4 py-3'):
            ui.icon('vpn_key', size='28px').classes('text-white')
            ui.label('授权设置').classes('text-xl font-bold text-white')
            ui.space()
        with ui.column().classes('w-full gap-4 px-4 py-4'):
            ui.label('服务端 API Key 设置').classes('text-lg font-bold')
            ui.label('此处配置用于调用远程服务端的 API Key，购买后由服务商提供。').classes('text-sm text-gray-500')

            state = {'full_key': getattr(config, 'PROXY_API_KEY', '') or ''}
            key_input = ui.input('API Key', value=mask_key(state['full_key'])).props('outlined').classes('w-full')
            with key_input.add_slot('append'):
                def toggle_visibility():
                    if key_input.value == mask_key(state['full_key']):
                        key_input.value = state['full_key']
                        ui.notify('显示完整 Key，请勿泄露！', color='warning')
                    else:
                        key_input.value = mask_key(state['full_key'])
                ui.button(icon='visibility', on_click=toggle_visibility, color='none').props('flat round dense')

            async def save_config():
                import os
                val = key_input.value.strip()
                if not val:
                    ui.notify('请输入 API Key！', color='warning')
                    return
                if val != state['full_key'] and '*' in val:
                    ui.notify('Key 不完整（含星号），未修改。', color='warning')
                    return
                cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                found = False
                for i, line in enumerate(lines):
                    if line.strip().startswith('PROXY_API_KEY'):
                        lines[i] = f'PROXY_API_KEY = os.getenv("PROXY_API_KEY", "{val}")\n'
                        found = True
                        break
                if not found:
                    lines.append(f'PROXY_API_KEY = os.getenv("PROXY_API_KEY", "{val}")\n')
                with open(cfg_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                importlib.reload(config)
                state['full_key'] = val
                key_input.value = mask_key(val)
                ui.notify('API Key 已保存并生效！', color='positive')

            async def test_connection():
                import httpx
                import os
                api_key = state['full_key']
                base = config.PROXY_SERVER_URL.split('/execute-task')[0]
                try:
                    async with httpx.AsyncClient(timeout=8) as c:
                        r = await c.get(base + '/customer/status', headers={'X-API-Key': api_key})
                        info = r.json()
                    if info.get('valid'):
                        ui.notify(f"Key 有效！{info.get('plan_type', '')} 剩余 {info.get('remaining', '∞')} 次，到期 {info.get('expire_at', '不限')}", color='positive')
                    else:
                        ui.notify(f"Key 无效: {info.get('reason', '未知')}", color='negative')
                except Exception as e:
                    ui.notify(f"连接失败: {e}", color='negative')

            with ui.row().classes('w-full gap-2'):
                ui.button('保存 Key', on_click=save_config, icon='save', color='primary')
                ui.button('测试连接', on_click=test_connection, icon='wifi_tethering', color='secondary')
