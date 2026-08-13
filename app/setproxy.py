import asyncio
from nicegui import ui

def create_proxy_settings_ui():
    """
    Creates the entire UI for the proxy settings page (Button 3),
    which includes cards for both listening and sending proxies.
    """
    
    def _create_single_proxy_card(title: str, config_path: str):
        """Helper function to create one proxy configuration card."""
        with ui.card().classes('w-full max-w-md'):
            ui.label(title).classes('text-2xl')
            enabled_switch = ui.switch('启用代理')
            ui.input('代理类型', value='SOCKS5').props('readonly')
            host_input = ui.input('代理主机')
            port_input = ui.number('代理端口', value=1080, format='%.0f')
            user_input = ui.input('用户名')
            pass_input = ui.input('密码', password=True, password_toggle_button=True)
            
            async def load_and_populate():
                """Loads proxy settings from a given .py file."""
                def sync_load_from_disk():
                    try:
                        with open(config_path, 'r', encoding='utf-8') as f:
                            exec_namespace = {}
                            exec(f.read(), exec_namespace)
                            return exec_namespace
                    except FileNotFoundError:
                        return {} # Return empty if not found, it's not an error
                    except Exception as e:
                        ui.notify(f'加载 {config_path} 时出错: {e}', color='negative')
                        return {}
                
                config_data = await asyncio.to_thread(sync_load_from_disk)
                enabled_switch.value = config_data.get('PROXY_ENABLED', False)
                host_input.value = config_data.get('PROXY_HOST', '')
                port_input.value = config_data.get('PROXY_PORT', 1080)
                user_input.value = config_data.get('PROXY_USERNAME', '')
                pass_input.value = config_data.get('PROXY_PASSWORD', '')

            async def save_config():
                """Saves the current UI state to the .py file."""
                content = (f"PROXY_ENABLED = {enabled_switch.value}\nPROXY_TYPE = \"SOCKS5\"\n"
                           f"PROXY_HOST = \"{host_input.value or ''}\"\n"
                           f"PROXY_PORT = {int(port_input.value or 1080)}\n"
                           f"PROXY_USERNAME = \"{user_input.value or ''}\"\n"
                           f"PROXY_PASSWORD = \"{pass_input.value or ''}\"\n")
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    ui.notify(f'{title} 已成功保存！', color='positive')
                except Exception as e:
                    ui.notify(f'保存至 {config_path} 时出错: {e}', color='negative')
            
            ui.button('保存配置', on_click=save_config).classes('mt-4')
            # Load the config shortly after the UI is created
            ui.timer(0.2, load_and_populate, once=True)

    with ui.row().classes('w-full no-wrap justify-center gap-8'):
        _create_single_proxy_card(title='健康检查专用代理', config_path='proxy_config.py')
        _create_single_proxy_card(title='私信发送账号代理', config_path='proxy_config_us1.py')