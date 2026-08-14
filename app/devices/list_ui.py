import asyncio

from nicegui import ui

from . import db_logic


def create_device_list_ui():
    state = {'page': 1, 'page_size': 20, 'items': []}

    def format_value(value):
        return '-' if value in (None, '') else str(value)

    def format_time(value):
        if value in (None, ''):
            return '-'
        s = str(value)

        if len(s) >= 10 and s[4] == '-' and s[7] == '-':
            return s[2:]
        return s

    def render_table():
        total = len(state['items'])
        total_pages = max(1, (total + state['page_size'] - 1) // state['page_size'])
        state['page'] = max(1, min(state['page'], total_pages))
        start = (state['page'] - 1) * state['page_size']
        end = start + state['page_size']
        page_items = state['items'][start:end]

        table_container.clear()
        with table_container:
            for item in page_items:
                with ui.row().classes('w-full items-center no-wrap gap-2 px-2 py-2 border-b border-gray-200 dark:border-gray-700 text-sm hover:bg-gray-50 dark:hover:bg-gray-800'):
                    fail_days = item.get('consecutive_fail_days')
                    icon = '🟢' if fail_days in (None, '', 0) else ('🟡' if fail_days == 1 else '🔴')
                    ui.label(f'{icon} {format_value(item.get("nickname"))}').classes('w-[16%] truncate text-blue-600 dark:text-blue-300')
                    ui.label(format_value(item.get('userid'))).classes('w-[24%] break-all')
                    ui.label(format_time(item.get('register_time'))).classes('w-[13%] truncate')
                    ui.label(format_time(item.get('next_send_time'))).classes('w-[13%] truncate')
                    ui.label(format_value(item.get('consecutive_fail_days'))).classes('w-[7%]')
                    ui.label(format_value(item.get('remarks'))).classes('w-[10%] truncate')
                    ui.label(format_time(item.get('added_time'))).classes('w-[17%] truncate')

        page_info.text = f'第 {state["page"]} / {total_pages} 页，共 {total} 条'
        paginator.max = total_pages
        paginator.set_value(state['page'])
        paginator.set_visibility(total_pages > 1)

    async def load_items():
        state['items'] = await asyncio.to_thread(db_logic.get_all_devices_list)
        state['page'] = 1
        render_table()

    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-cyan-600 to-blue-600 rounded-t-2xl px-4 py-3'):
            ui.icon('view_list', size='28px').classes('text-white')
            ui.label('设备列表').classes('text-xl font-bold text-white')
            ui.space()
            ui.button('刷新', icon='refresh', on_click=load_items, color='white').props('flat text-color=primary')

        with ui.column().classes('w-full gap-4 px-4 py-4'):
            with ui.row().classes('w-full items-center no-wrap gap-2 px-2 py-2 font-semibold bg-gradient-to-r from-gray-100 to-gray-50 dark:from-gray-800 dark:to-gray-700 rounded-lg text-sm'):
                ui.label('Nickname').classes('w-[16%]')
                ui.label('UserID').classes('w-[24%]')
                ui.label('注册时间').classes('w-[13%]')
                ui.label('下次发送时间').classes('w-[13%]')
                ui.label('连续失败天数').classes('w-[7%]')
                ui.label('备注').classes('w-[10%]')
                ui.label('添加时间').classes('w-[17%]')

            table_container = ui.column().classes('w-full gap-0')
            page_info = ui.label('').classes('text-sm text-gray-500')
            paginator = ui.pagination(1, 1).props('boundary-numbers')

            def on_page_change(e):
                state['page'] = int(e.args) if e.args is not None else 1

                render_table()

            paginator.on('update:model-value', on_page_change)

    ui.timer(0.1, load_items, once=True)
