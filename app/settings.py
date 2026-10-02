import asyncio
import importlib
import re
from typing import Dict
from nicegui import ui, elements
import config as _config_module

CONFIG_FILE_PATH = 'config.py'


def mask_user_id(uid: str) -> str:
    """脱敏：保留前部，后4位用*号；短id全星号"""
    if not uid:
        return ''
    if len(uid) <= 4:
        return '*' * len(uid)
    return uid[:-4] + '****'


def _section_title(text: str, icon: str = 'settings'):
    """渐变风格分区标题"""
    with ui.row().classes('w-full items-center gap-2 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg px-3 py-2'):
        ui.icon(icon).classes('text-white')
        ui.label(text).classes('text-white font-semibold')


def _seconds_to_human(sec) -> str:
    """秒 -> 可读时间。

    ≤ 72 小时：显示 时:分:秒（如 03:00:00、24:00:00）
    >  72 小时：显示 天时.分.秒（如 30天0时0分0秒）
    """
    try:
        sec = int(round(float(sec)))
    except (TypeError, ValueError):
        return str(sec)
    if sec < 0:
        sec = 0
    if sec > 72 * 3600:
        days, rem = divmod(sec, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        return f'{days}天{hours}时{minutes}分{seconds}秒'
    hours, rem = divmod(sec, 3600)
    minutes, seconds = divmod(rem, 60)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d}'


def _human_to_seconds(text):
    """可读时间 -> 秒。支持 时:分:秒、分:秒、纯数字秒、天时.分.秒。

    解析失败返回 None。
    """
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    if re.fullmatch(r'\d+', s):
        return int(s)
    if ':' in s:
        try:
            parts = [int(p) for p in s.split(':')]
        except ValueError:
            return None
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return None
    m = re.fullmatch(r'\s*(?:(\d+)\s*天)?\s*(?:(\d+)\s*时)?\s*(?:(\d+)\s*分)?\s*(?:(\d+)\s*秒)?\s*', s)
    if m and any(g is not None for g in m.groups()):
        d, h, mi, se = (int(g) if g else 0 for g in m.groups())
        return d * 86400 + h * 3600 + mi * 60 + se
    return None


_TIME_LADDER = [
    5, 10, 15, 30, 45, 60, 120, 180, 300, 600, 900, 1800, 3600,
    7200, 10800, 14400, 21600, 43200, 86400, 129600, 172800, 259200,
    604800, 1209600, 2592000, 5184000, 7776000,
]


def _current_seconds(key):
    """从当前内存 config 读取某参数的秒数（读不到返回 None）。"""
    try:
        v = getattr(_config_module, key, None)
        return int(v) if v is not None else None
    except Exception:
        return None


def _build_stops(key):
    """构造某参数的滑块档位：常用档位 ∪ {当前配置值} ∪ {出厂默认值}，升序去重。"""
    stops = set(_TIME_LADDER)
    cur = _current_seconds(key)
    if cur is not None:
        stops.add(cur)
    fac = _FACTORY_DEFAULTS.get(key)
    if fac is not None:
        stops.add(int(fac))
    return sorted(stops)


def _nearest_index(stops, secs):
    """返回最接近 secs 的档位下标。"""
    if secs is None or not stops:
        return 0
    best_i, best_d = 0, None
    for i, s in enumerate(stops):
        d = abs(s - secs)
        if best_d is None or d < best_d:
            best_i, best_d = i, d
    return best_i


_UI_CSS_INJECTED = {'done': False}
_ROUNDED_RADIO_CSS = '''
/* 圆角背景单选组：紧凑尺寸 */
.rounded-radio .q-radio {
    background-color: #eef2ff;
    border: 1px solid #c7d2fe;
    border-radius: 10px;
    padding: 4px 14px;
    min-height: 36px;
    margin-right: 8px;
    transition: background-color .2s ease, border-color .2s ease;
}
.rounded-radio .q-radio:hover {
    background-color: #e0e7ff;
    border-color: #a5b4fc;
}
.rounded-radio .q-radio .q-radio__inner {
    font-size: 1.15em;
}
.rounded-radio .q-radio .q-radio__label {
    font-size: 14px;
    font-weight: 500;
}
/* 被选中项：绿色背景 + 白字（选中态由 Quasar 的 .q-radio__inner--truthy 标记）*/
.rounded-radio .q-radio:has(.q-radio__inner--truthy),
.rounded-radio .q-radio:has(input[type="radio"]:checked) {
    background-color: #16a34a;
    border-color: #15803d;
}
.rounded-radio .q-radio:has(.q-radio__inner--truthy):hover,
.rounded-radio .q-radio:has(input[type="radio"]:checked):hover {
    background-color: #15803d;
    border-color: #166534;
}
.rounded-radio .q-radio:has(.q-radio__inner--truthy) .q-radio__label,
.rounded-radio .q-radio:has(input[type="radio"]:checked) .q-radio__label {
    color: #ffffff;
}
.rounded-radio .q-radio:has(.q-radio__inner--truthy) .q-radio__inner,
.rounded-radio .q-radio:has(input[type="radio"]:checked) .q-radio__inner {
    color: #ffffff;
}
body.body--dark .rounded-radio .q-radio {
    background-color: #1e293b;
    border-color: #334155;
}
body.body--dark .rounded-radio .q-radio:hover {
    background-color: #334155;
    border-color: #475569;
}
body.body--dark .rounded-radio .q-radio:has(.q-radio__inner--truthy),
body.body--dark .rounded-radio .q-radio:has(input[type="radio"]:checked) {
    background-color: #16a34a;
    border-color: #15803d;
}
body.body--dark .rounded-radio .q-radio:has(.q-radio__inner--truthy):hover,
body.body--dark .rounded-radio .q-radio:has(input[type="radio"]:checked):hover {
    background-color: #15803d;
    border-color: #166534;
}
'''


_TASK_PARAM_KEYS = (
    'SUCCESS_SEND_INTERVAL',
    'FIRST_FAILURE_COOLDOWN_INTERVAL',
    'FAILURE_COOLDOWN_INTERVAL',
    'FAILURE_COOLDOWN_30_DAYS',
    'TASK_INTERVAL',
    'USER_ID_POLLING_INTERVAL',
    'USER_POLLING_INTERVAL',
    'MAX_RETRY_ATTEMPTS',
    'MAX_DAILY_USAGE',
)

_FACTORY_DEFAULTS = {
    'SUCCESS_SEND_INTERVAL': 10800,
    'FIRST_FAILURE_COOLDOWN_INTERVAL': 30,
    'FAILURE_COOLDOWN_INTERVAL': 86400,
    'FAILURE_COOLDOWN_30_DAYS': 2592000,
    'TASK_INTERVAL': 35,
    'USER_ID_POLLING_INTERVAL': 60,
    'USER_POLLING_INTERVAL': 60,
    'MAX_RETRY_ATTEMPTS': 2,
    'MAX_DAILY_USAGE': 1,
}


def create_settings_ui():
    if not _UI_CSS_INJECTED['done']:
        ui.add_css(_ROUNDED_RADIO_CSS)
        _UI_CSS_INJECTED['done'] = True

    inputs: Dict[str, elements.ValueElement] = {}
    time_keys = set()
    time_sliders = {}
    full_user_id = {'value': ''}

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

        for key in time_keys:
            if key not in config_data:
                continue
            info = time_sliders.get(key)
            if not info:
                continue
            secs = config_data[key]
            info['slider'].set_value(_nearest_index(info['stops'], secs))
            info['label'].set_text(_seconds_to_human(secs))

        if 'CHECK_USER_ID' in config_data and config_data['CHECK_USER_ID']:
            full_user_id['value'] = config_data['CHECK_USER_ID']
            inputs['CHECK_USER_ID'].set_value(mask_user_id(config_data['CHECK_USER_ID']))

        try:
            _sync_card_style_visibility()
        except Exception:
            pass

        ui.notify('配置已加载', color='positive')

    async def save_config():
        config_values = {key: element.value for key, element in inputs.items()}
        for key in time_keys:
            info = time_sliders.get(key)
            if info and info['slider'].value is not None:
                config_values[key] = info['stops'][int(info['slider'].value)]

        uid_val = inputs['CHECK_USER_ID'].value
        if full_user_id['value'] and uid_val in (mask_user_id(full_user_id['value']), full_user_id['value']):
            config_values['CHECK_USER_ID'] = full_user_id['value']

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

                importlib.reload(_config_module)

                return True, ""

            except Exception as e:
                return False, str(e)

        success, msg = await asyncio.to_thread(sync_save)
        if success:
            for key in time_keys:
                info = time_sliders.get(key)
                if info and info['slider'].value is not None:
                    info['label'].set_text(_seconds_to_human(info['stops'][int(info['slider'].value)]))
            ui.notify('配置文件已成功保存！', color='positive')
        else:
            ui.notify(f'保存失败: {msg}', color='negative', multi_line=True)

    def reset_task_params():
        """把"任务与连接参数"卡片内的控件恢复为固定的出厂默认值。"""
        restored = 0
        for key in _TASK_PARAM_KEYS:
            if key not in _FACTORY_DEFAULTS:
                continue
            val = _FACTORY_DEFAULTS[key]
            if key in time_sliders:
                info = time_sliders[key]
                secs = int(val)
                info['slider'].set_value(_nearest_index(info['stops'], secs))
                info['label'].set_text(_seconds_to_human(secs))
                restored += 1
            elif key in inputs:
                inputs[key].set_value(val)
                restored += 1
        ui.notify(f'已恢复出厂默认值（共 {restored} 项），请点"保存所有配置"使其生效。', color='positive', multi_line=True)

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
                card_extra = None

                def _sync_card_style_visibility():
                    """发送模式 = 卡片+文本(3) 时才显示提示语与卡片样式选项。"""
                    if card_extra is None:
                        return
                    try:
                        card_extra.set_visibility(inputs['MESSAGE_SEND_MODE'].value == 3)
                    except Exception:
                        pass

                with ui.row().classes('w-full bg-gray-100 dark:bg-gray-800 p-2 rounded-lg mt-2'):
                    inputs['MESSAGE_SEND_MODE'] = (ui.radio(send_mode_options, value=1)
                                                   .props('inline').classes('rounded-radio')
                                                   .on_value_change(_sync_card_style_visibility))

                card_extra = ui.column().classes('w-full gap-0')
                with card_extra:
                    ui.label('（⚠️注：根据小红书官方私信规则，陌生人只能1条私信，除非对方回复消息，否则"卡片+文本"模式只能送达卡片）').classes('text-sm text-red-500 font-medium mt-1')
                    card_style_row = ui.row().classes('w-full items-center gap-2 mt-2')
                    with card_style_row:
                        ui.label('卡片样式：').classes('text-sm font-medium')
                        inputs['CARD_AND_TEXT_CARD'] = ui.radio({1: '卡片➊', 2: '卡片➋'}, value=1).props('inline').classes('rounded-radio')
                _sync_card_style_visibility()

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
                    ui.icon('help_outline', color='grey', size='sm').tooltip('用于账号健康检测的云托管监测号。需要申请企业私信通账户，并且配置AI回复。')
                    check_uid_input = ui.input('云托管监测号UserId(默认留空即可)').props('style="width: 300px"')
                    inputs['CHECK_USER_ID'] = check_uid_input

                    def toggle_check_uid():
                        """眼睛按钮：切换 脱敏值 <-> 完整值"""
                        if check_uid_input.value == full_user_id['value'] and full_user_id['value']:
                            check_uid_input.set_value(mask_user_id(full_user_id['value']))
                        else:
                            check_uid_input.set_value(full_user_id['value'])

                    ui.button(icon='visibility', on_click=toggle_check_uid, color='transparent').props('flat round dense').classes('-ml-1').tooltip('点击查看完整UserId')

            with ui.grid(columns=2).classes('w-full gap-4'):
                with ui.card().classes('w-full'):
                    _section_title('数据库设置', 'storage')
                    with ui.column().classes('w-full items-center gap-2 mt-2'):
                        inputs['MONGO_HOST'] = ui.input('主机').classes('w-full max-w-md')
                        inputs['MONGO_PORT'] = ui.number('端口(默认)', format='%.0f').classes('w-full max-w-md')
                        inputs['MONGO_USERNAME'] = ui.input('数据库用户名').classes('w-full max-w-md')
                        inputs['MONGO_PASSWORD'] = ui.input('数据库密码', password=True).classes('w-full max-w-md')
                        inputs['MONGO_AUTH_SOURCE'] = ui.input('授权(默认)').classes('w-full max-w-md')
                        inputs['MONGO_DB_NAME'] = ui.input('数据库名称').classes('w-full max-w-md')
                    ui.space()
                    _section_title('数据库集合设置', 'folder')
                    with ui.column().classes('w-full items-center gap-2 mt-2'):
                        inputs['MONGO_DEVICE_COLLECTION'] = ui.input('设备集').classes('w-full max-w-md')
                        inputs['MONGO_USER_ID_COLLECTION'] = ui.input('UserID集(UserID管理)').classes('w-full max-w-md')
                        inputs['MONGO_SEND_TEXT_COLLECTION'] = ui.input('发送文本集').classes('w-full max-w-md')

                with ui.card().classes('w-full'):
                    _section_title('任务与连接参数', 'timer')

                    def create_number_input(key: str, label: str, tooltip: str):
                        el = inputs[key] = ui.number(label, format='%.0f')
                        with el.add_slot('append'):
                            ui.icon('help_outline', color='grey', size='xs').tooltip(tooltip)
                        return el

                    def create_time_slider(key: str, label: str, tooltip: str):
                        """时间参数滑块：档位为常用时长（秒），默认停在当前配置值。

                        拖动时上方实时显示 时:分:秒（>72小时显示 天时.分.秒）。
                        """
                        time_keys.add(key)
                        stops = _build_stops(key)
                        idx = _nearest_index(stops, _current_seconds(key))
                        with ui.column().classes('w-full max-w-md gap-0 py-1'):
                            with ui.row().classes('w-full items-center gap-1 no-wrap'):
                                ui.label(label).classes('text-sm font-medium')
                                ui.icon('help_outline', color='grey', size='xs').tooltip(tooltip)
                                ui.space()
                                val_lbl = ui.label(_seconds_to_human(stops[idx])).classes('text-sm font-semibold text-blue-600 dark:text-blue-300')
                            sl = ui.slider(min=0, max=len(stops) - 1, value=idx, step=1).props('dense')
                            time_sliders[key] = {'stops': stops, 'slider': sl, 'label': val_lbl}

                            def _on_change(e, _k=key):
                                info = time_sliders[_k]
                                raw = getattr(e, 'value', None)
                                if raw is None:
                                    raw = getattr(e, 'args', None)
                                if raw is None:
                                    raw = e
                                try:
                                    i = int(raw)
                                except (TypeError, ValueError):
                                    return
                                i = max(0, min(i, len(info['stops']) - 1))
                                info['label'].set_text(_seconds_to_human(info['stops'][i]))

                            sl.on_value_change(_on_change)
                        return sl

                    with ui.column().classes('w-full items-center gap-2 mt-2'):
                        create_time_slider('SUCCESS_SEND_INTERVAL', '成功冷却时间', '一条私信成功发送后，该账号需要等待多久才能发送下一条。')
                        create_time_slider('FIRST_FAILURE_COOLDOWN_INTERVAL', '首次失败冷却时间', '账号当天首次失败后的冷却时间，给一次重试机会，避免网络临时问题误伤。')
                        create_time_slider('FAILURE_COOLDOWN_INTERVAL', '连续失败冷却时间', '账号当天连续失败后的冷却时间，一般设 24:00:00。')
                        create_time_slider('FAILURE_COOLDOWN_30_DAYS', '跨天连续失败冷却时间', '连续两天健康检查都失败后的冷却时间，一般为 30天0时0分0秒。')
                        create_time_slider('TASK_INTERVAL', '下个任务时间', '获取下一个任务的间隔时间。')
                        create_time_slider('USER_ID_POLLING_INTERVAL', '私信接收方补充时间', '每隔多久检查一次数据库，补充新的私信接收者（UserID）。')
                        create_time_slider('USER_POLLING_INTERVAL', '私信发送方补充时间', '每隔多久检查一次数据库，补充新的私信发送账号。')
                        create_number_input('MAX_RETRY_ATTEMPTS', '单任务最大重试次数', '单个任务流程（含等待接收方）的最大重试次数；账号每日测活次数已固定为 2 次，无需在此调整。').classes('w-full max-w-md')
                        create_number_input('MAX_DAILY_USAGE', '私信发送方当日使用次数', '每个私信发送账号每天最多能发送多少条私信。').classes('w-full max-w-md')
                    ui.space()
                    with ui.row().classes('w-full justify-center pt-2 border-t border-gray-200 dark:border-gray-700 mt-2'):
                        ui.button('恢复默认', icon='restart_alt', on_click=reset_task_params).props('outline color=grey-8').classes('mt-2')

        with ui.row().classes('w-full justify-center gap-4 mt-2 pb-4'):
            ui.button('保存所有配置', on_click=save_config, icon='save', color='primary').classes('px-8')
            ui.button('重新加载配置', on_click=load_config, icon='refresh', color='secondary').classes('px-8')

    ui.timer(0.2, load_config, once=True)
