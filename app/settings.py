import asyncio
import re
from typing import Dict
from nicegui import ui, elements

CONFIG_FILE_PATH = 'config.py'


def _section_title(text: str, icon: str = 'settings'):
                  
    with ui.row().classes('w-full items-center gap-2 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg px-3 py-2'):
        ui.icon(icon).classes('text-white')
        ui.label(text).classes('text-white font-semibold')


def create_settings_ui():
    inputs: Dict[str, elements.ValueElement] = {}

    async def load_config():
        def sync_load():
            try:
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    content = f.read()
                namespace = {}
                exec(content, namespace)
                return namespace
            except Exception as e:
                ui.notify(f'加载配置文件失败: {e}', color='negative', multi_line=True)
                return {}

        config_data = await asyncio.to_thread(sync_load)
        if not config_data:
            return

        for key, element in inputs.items():
            if key in config_data:
                element.set_value(config_data[key])
        ui.notify('配置已加载', color='positive')

    async def save_config():
        config_values = {key: element.value for key, element in inputs.items()}

        def sync_save():
            try:
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                new_lines = []
                for line in lines:
                    stripped_line = line.strip()

                    if not stripped_line or stripped_line.startswith('#') or '"""' in stripped_line:
                        new_lines.append(line)
                        continue

                    line_updated = False
                    for key, value in config_values.items():
                        if re.match(rf'^{key}\s*=', stripped_line):
                            indent = line[:len(line) - len(line.lstrip())]
                            comment = ''
                            if '#' in line:
                                comment = '  #' + line.split('#', 1)[1].strip()

                            if isinstance(value, str):
                                escaped_value = value.replace('\\', '\\\\').replace("'", "\\'")
                                formatted_value = f"'{escaped_value}'"
                            else:
                                formatted_value = int(value)

                            new_line = f"{indent}{key} = {formatted_value}{comment}\n"
                            new_lines.append(new_line)
                            line_updated = True
                            break

                    if not line_updated:
                        new_lines.append(line)

                with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)

                return True, ""

            except Exception as e:
                return False, str(e)

        success, msg = await asyncio.to_thread(sync_save)
        if success:
            ui.notify('配置文件已成功保存！', color='positive')
        else:
            ui.notify(f'保存失败: {msg}', color='negative', multi_line=True)

    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-indigo-600 to-purple-600 rounded-t-2xl px-4 py-3'):
            ui.icon('tune', size='28px').classes('text-white')
            ui.label('软件设置').classes('text-xl font-bold text-white')


        with ui.column().classes('w-full gap-4 px-4 py-4'):
            with ui.card().classes('w-full'):
                with ui.row().classes('w-full items-center gap-2'):
                    ui.icon('send', size='sm').classes('text-blue-500')
                    ui.label('消息发送模式').classes('text-lg font-semibold text-blue-600 dark:text-blue-300')

                send_mode_options = {
                    1: '卡片➊',
                    4: '卡片➋',
                    2: '文本',
                    3: '卡片+文本'
                }
                with ui.row().classes('w-full bg-gray-100 dark:bg-gray-800 p-3 rounded-lg mt-2'):
                    inputs['MESSAGE_SEND_MODE'] = ui.radio(send_mode_options, value=1).props('inline')
                ui.label('（⚠️注：根据小红书官方私信规则，陌生人只能1条私信，除非对方回复消息，否则"卡片+文本"模式只能送达卡片）').classes('text-sm text-red-500 font-medium mt-1')

                with ui.row().classes('w-full items-center gap-2 mt-2'):
                    ui.label('【卡片+文本】模式使用的卡片:').classes('text-sm font-medium')
                    inputs['CARD_AND_TEXT_CARD'] = ui.radio({1: '卡片➊', 2: '卡片➋'}, value=1).props('inline')

                def create_text_input(key: str, label: str, tooltip: str, props: str = ''):
                    el = inputs[key] = ui.input(label).props(props)
                    with el.add_slot('append'):
                        ui.icon('help_outline', color='grey', size='xs').tooltip(tooltip)
                    return el

            with ui.card().classes('w-full'):
                with ui.row().classes('w-full items-center gap-2'):
                    ui.icon('favorite', size='sm').classes('text-rose-500')
                    ui.label('健康检查设置').classes('text-lg font-semibold text-rose-600 dark:text-rose-300')
                with ui.row().classes('w-full items-center gap-4 mt-2'):
                    create_text_input('CHECK_USER_ID', '收发信主账号UserId(此号不参与群发)',
                                      '用于检测小红书账发信账账号健康状态。此UuerID务必需要正常可收发信账号。',
                                      props='style="width: 250px"')

            with ui.grid(columns=2).classes('w-full gap-4'):
                with ui.card().classes('w-full'):
                    _section_title('数据库设置', 'storage')
                    with ui.column().classes('w-full items-center gap-2 mt-2'):
                        inputs['MONGO_HOST'] = ui.input('主机').classes('w-full max-w-md')
                        inputs['MONGO_PORT'] = ui.number('端口(默认)', format='%.0f').classes('w-full max-w-md')
                        inputs['MONGO_USERNAME'] = ui.input('数据库用户名').classes('w-full max-w-md')
                        inputs['MONGO_PASSWORD'] = ui.input('数据库密码', password=True).classes('w-full max-w-md')
                        inputs['MONGO_AUTH_SOURCE'] = ui.input('授权(默认)').classes('w-full max-w-md')
                    ui.space()
                    _section_title('数据库集合设置', 'folder')
                    with ui.column().classes('w-full items-center gap-2 mt-2'):
                        inputs['MONGO_DB_NAME'] = ui.input('数据库名称').classes('w-full max-w-md')
                        inputs['MONGO_DEVICE_COLLECTION'] = ui.input('设备集').classes('w-full max-w-md')
                        inputs['MONGO_USER_ID_COLLECTION'] = ui.input('UserID集(UserID管理)').classes('w-full max-w-md')
                        inputs['MONGO_SEND_TEXT_COLLECTION'] = ui.input('发送文本集').classes('w-full max-w-md')
                        inputs['MONGO_CHECK_STATUS_COLLECTION'] = ui.input('状态码检测集(默认)').classes('w-full max-w-md')

                with ui.card().classes('w-full'):
                    _section_title('任务与连接参数', 'timer')

                    def create_number_input(key: str, label: str, tooltip: str):
                        el = inputs[key] = ui.number(label, format='%.0f')
                        with el.add_slot('append'):
                            ui.icon('help_outline', color='grey', size='xs').tooltip(tooltip)
                        return el

                    with ui.column().classes('w-full items-center gap-2 mt-2'):
                        create_number_input('DEFAULT_SOCKET_TIMEOUT', 'Socket 超时 (秒)', '与代理或目标服务器建立连接和等待响应的最长时间。').classes('w-full max-w-md')
                        create_number_input('RECONNECT_DELAY', 'IP连接失败间隔 (秒)', '当一个IP地址连接失败后，需要等待多少秒才能再次使用该IP。').classes('w-full max-w-md')
                        create_number_input('SUCCESS_SEND_INTERVAL', '成功冷却时间 (秒)', '一条私信成功发送后，该账号需要等待多少秒才能发送下一条。').classes('w-full max-w-md')
                        create_number_input('FAILURE_COOLDOWN_INTERVAL', '首次失败冷却时间 (秒)', '一条私信发送失败后，需要等待多少秒才能进行下一次尝试。').classes('w-full max-w-md')
                        create_number_input('FAILURE_COOLDOWN_30_DAYS', '连续失败冷却时间 (秒)', '当账号健康检查为异常时，需冷却多少秒再查，一般是30天。').classes('w-full max-w-md')
                        create_number_input('INITIAL_MESSAGE_DELAY', '检查完成发送消息间隔 (秒)', '账号健康检查通过后，延迟多少秒再开始发送第一条私信。').classes('w-full max-w-md')
                        create_number_input('TASK_INTERVAL', '下个任务时间 (秒)', '获取下一个任务的间隔时间。').classes('w-full max-w-md')
                        create_number_input('USER_ID_POLLING_INTERVAL', '私信接收方补充时间 (秒)', '每隔多少秒检查一次数据库，补充新的私信接收者（UserID）。').classes('w-full max-w-md')
                        create_number_input('USER_POLLING_INTERVAL', '私信发送方补充时间 (秒)', '每隔多少秒检查一次数据库，补充新的私信发送账号。').classes('w-full max-w-md')
                        create_number_input('MAX_RETRY_ATTEMPTS', '健康检查当日重试次数', '如果账号健康检查失败，单日可以重试的次数。').classes('w-full max-w-md')
                        create_number_input('MAX_DAILY_USAGE', '私信发送方当日使用次数', '每个私信发送账号每天最多能发送多少条私信。').classes('w-full max-w-md')

        with ui.row().classes('w-full justify-center gap-4 mt-2 pb-4'):
            ui.button('保存所有配置', on_click=save_config, icon='save', color='primary').classes('px-8')
            ui.button('重新加载配置', on_click=load_config, icon='refresh', color='secondary').classes('px-8')

    ui.timer(0.2, load_config, once=True)
