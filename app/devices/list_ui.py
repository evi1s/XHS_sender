import asyncio
import math
from datetime import datetime

from nicegui import ui

from . import db_logic


def create_device_list_ui():
    state = {'page': 1, 'page_size': 20, 'items': []}
    cooldown_refs = []                                        

    def format_value(value):
        return '-' if value in (None, '') else str(value)

    def format_time(value):
        if value in (None, ''):
            return '-'
        s = str(value)
                                                           
        if len(s) >= 10 and s[4] == '-' and s[7] == '-':
            return s[2:]
        return s

    def parse_next_time(value):
        if value in (None, ''):
            return None
        if isinstance(value, datetime):
            return value
        s = str(value).strip()
        if not s:
            return None
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M:%S'):
            try:
                return datetime.strptime(s[:19], fmt)
            except Exception:
                continue
        return None

    def cooldown_minutes(target):
        if target is None:
            return None
        delta = target - datetime.now()
        total_seconds = delta.total_seconds()
        if total_seconds <= 0:
            return 0
        return math.ceil(total_seconds / 60)

    def format_cooldown(minutes):
        if minutes is None:
            return '-'
        if minutes <= 0:
            return '✅'
        total_days = minutes / 1440.0
        if total_days >= 30:
            months = int(total_days // 30)
            days = int(total_days % 30)
            if days > 0:
                return f'{months}个月{days}天'
            return f'{months}个月'
        days, rem = divmod(minutes, 1440)
        if days > 0:
            hours, mins = divmod(rem, 60)
            return f'{days}天{hours}小时{mins:02d}分'
        hours, mins = divmod(minutes, 60)
        if hours > 0:
            return f'{hours}小时{mins:02d}分'
        return f'{mins}分钟'

    def cooldown_ready(minutes):
        return minutes is not None and minutes <= 0

    def mask_userid(uid):
                                    
        uid = format_value(uid)
        if not uid or uid == '-':
            return uid
        if len(uid) <= 8:
            return '*' * len(uid)
        return uid[:-8] + '*' * 8

    def _toggle_uid(lbl, raw):
                            
        if '*' in lbl.text:
            lbl.set_text(raw)
        else:
            lbl.set_text(mask_userid(raw))

    def render_table():
        total = len(state['items'])
        total_pages = max(1, (total + state['page_size'] - 1) // state['page_size'])
        state['page'] = max(1, min(state['page'], total_pages))
        start = (state['page'] - 1) * state['page_size']
        end = start + state['page_size']
        page_items = state['items'][start:end]

        cooldown_refs.clear()
        table_container.clear()
        with table_container:
            for item in page_items:
                with ui.row().classes('w-full items-center no-wrap gap-2 px-2 py-2 border-b border-gray-200 dark:border-gray-700 text-sm hover:bg-gray-50 dark:hover:bg-gray-800'):
                    fail_days = item.get('consecutive_fail_days')
                    icon = '🟢' if fail_days in (None, '', 0) else ('🟡' if fail_days == 1 else '🔴')
                    ui.label(f'{icon} {format_value(item.get("nickname"))}').classes('w-[13%] truncate text-blue-600 dark:text-blue-300')
                    _uid_raw = format_value(item.get('userid'))
                    _uid_lbl = ui.label(mask_userid(_uid_raw)).classes('w-[21%] break-all cursor-pointer text-blue-600 dark:text-blue-300 hover:underline')
                    _uid_lbl.on('click', lambda e, lbl=_uid_lbl, raw=_uid_raw: _toggle_uid(lbl, raw))
                    ui.label(format_time(item.get('register_time'))).classes('w-[11%] truncate')
                    ui.label(format_time(item.get('next_send_time'))).classes('w-[11%] truncate')
                                                                          
                    target = parse_next_time(item.get('next_send_time'))
                    minutes = cooldown_minutes(target)
                    lbl = ui.label(format_cooldown(minutes)).classes('w-[12%] font-medium')
                    if cooldown_ready(minutes):
                        lbl.classes('text-green-600')
                    else:
                        lbl.classes('text-amber-600')
                    if minutes is not None:
                        cooldown_refs.append((lbl, target))
                    ui.label(format_value(item.get('consecutive_fail_days'))).classes('w-[7%]')
                    ui.label(format_value(item.get('remarks'))).classes('w-[8%] truncate')
                    ui.label(format_time(item.get('added_time'))).classes('w-[17%] truncate')

        page_info.text = f'第 {state["page"]} / {total_pages} 页，共 {total} 条'
        paginator.max = total_pages
        paginator.set_value(state['page'])
        paginator.set_visibility(total_pages > 1)

    def refresh_cooldown():
        for lbl, target in list(cooldown_refs):
            minutes = cooldown_minutes(target)
            lbl.set_text(format_cooldown(minutes))
            if cooldown_ready(minutes):
                lbl.classes(add='text-green-600', remove='text-amber-600')
            else:
                lbl.classes(add='text-amber-600', remove='text-green-600')

    async def load_items():
        state['items'] = await asyncio.to_thread(db_logic.get_all_devices_list)
        state['page'] = 1
        render_table()

    with ui.card().classes('w-full max-w-7xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-cyan-600 to-blue-600 rounded-t-2xl px-4 py-3'):
            ui.icon('view_list', size='28px').classes('text-white')
            ui.label('设备列表').classes('text-xl font-bold text-white')
            ui.space()
            ui.button('刷新', icon='refresh', on_click=load_items, color='white').props('flat text-color=primary')

        with ui.column().classes('w-full gap-4 px-4 py-4'):
            with ui.row().classes('w-full items-center no-wrap gap-2 px-2 py-2 font-semibold bg-gradient-to-r from-gray-100 to-gray-50 dark:from-gray-800 dark:to-gray-700 rounded-lg text-sm'):
                ui.label('Nickname').classes('w-[13%]')
                ui.label('UserID').classes('w-[21%]')
                ui.label('注册时间').classes('w-[11%]')
                ui.label('下次发送时间').classes('w-[11%]')
                ui.label('冷却时间').classes('w-[12%]')
                ui.label('连续失败天数').classes('w-[7%]')
                ui.label('备注').classes('w-[8%]')
                ui.label('添加时间').classes('w-[17%]')

            table_container = ui.column().classes('w-full gap-0')
            page_info = ui.label('').classes('text-sm text-gray-500')
            paginator = ui.pagination(1, 1).props('boundary-numbers')

            def on_page_change(e):
                state['page'] = int(e.args) if e.args is not None else 1
                render_table()

            paginator.on('update:model-value', on_page_change)

    ui.timer(0.1, load_items, once=True)
    ui.timer(60, refresh_cooldown)
