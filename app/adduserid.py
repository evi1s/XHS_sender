import asyncio
from nicegui import ui
from pymongo import ReturnDocument
import config
from database import connect_to_mongo, close_mongo_connection
from devices.data import get_devices_collection, get_collection


def create_ui():
    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-amber-500 to-orange-600 rounded-t-2xl px-4 py-3'):
            ui.icon('group_add', size='28px').classes('text-white')
            ui.label('客户管理').classes('text-xl font-bold text-white')
            ui.space()
        with ui.column().classes('w-full gap-4 px-4 py-4'):
            ui.label('管理 User ID').classes('text-lg font-bold text-amber-600 dark:text-amber-300')
            ui.label('逐条发送，自动清理客户ID。').classes('text-xs text-gray-400 -mt-1 ml-1')

            state = {'page': 1, 'page_size': 20, 'items': []}

            async def load_data(page: int = 1):
                state['page'] = page
                col = get_collection(config.MONGO_USER_ID_COLLECTION)
                total = col.count_documents({})
                total_pages = max(1, (total + state['page_size'] - 1) // state['page_size'])
                state['page'] = max(1, min(page, total_pages))
                skip = (state['page'] - 1) * state['page_size']
                cursor = col.find({}).sort('_id', 1).skip(skip).limit(state['page_size'])
                items = []
                for doc in cursor:
                    items.append({'user_id': doc.get('user_id', ''), 'claimed': doc.get('claimed', False)})
                state['items'] = items
                table_container.clear()
                with table_container:
                    if not items:
                        ui.label('暂无客户 ID').classes('text-gray-400 text-center w-full py-4')
                    for it in items:
                        with ui.row().classes('w-full items-center no-wrap gap-2 px-2 py-2 border-b border-gray-200 dark:border-gray-700'):
                            ui.label('🟢' if not it['claimed'] else '🔴').classes('w-8')
                            ui.label(it['user_id']).classes('flex-1 break-all')
                            ui.label('待发送' if not it['claimed'] else '已领取').classes('w-16 text-xs text-gray-500')
                page_info.text = f'第 {state["page"]} / {total_pages} 页，共 {total} 条'
                paginator.max = total_pages
                paginator.set_value(state['page'])
                paginator.set_visibility(total_pages > 1)

            async def add_userid():
                val = input_userid.value.strip()
                if not val:
                    ui.notify('请输入 UserID！', color='warning')
                    return
                col = get_collection(config.MONGO_USER_ID_COLLECTION)
                existing = col.find_one({'user_id': val})
                if existing:
                    ui.notify('该 UserID 已存在！', color='warning')
                    return
                col.insert_one({'user_id': val, 'claimed': False, 'claim_time': None})
                input_userid.value = ''
                ui.notify('添加成功！', color='positive')
                await load_data(state['page'])

            async def delete_userid():
                val = input_userid_del.value.strip()
                if not val:
                    ui.notify('请输入要删除的 UserID！', color='warning')
                    return
                col = get_collection(config.MONGO_USER_ID_COLLECTION)
                result = col.delete_many({'user_id': val})
                ui.notify(f'已删除 {result.deleted_count} 条', color='positive' if result.deleted_count else 'warning')
                input_userid_del.value = ''
                await load_data(state['page'])

            async def clear_all():
                with ui.dialog() as dialog, ui.card().classes('rounded-2xl p-6'):
                    ui.icon('warning', size='48px').classes('text-red-500 self-center')
                    ui.label('确定清空所有客户 ID？此操作不可撤销！').classes('text-lg font-bold self-center')
                    with ui.row().classes('w-full justify-end mt-4'):
                        ui.button('取消', on_click=dialog.close, color='gray')
                        ui.button('清空', on_click=lambda: dialog.submit('yes'), color='red')
                if await dialog == 'yes':
                    col = get_collection(config.MONGO_USER_ID_COLLECTION)
                    result = col.delete_many({})
                    ui.notify(f'已清空 {result.deleted_count} 条', color='positive')
                    await load_data(1)

            with ui.row().classes('w-full gap-2'):
                input_userid = ui.input('添加 UserID').props('outlined').classes('flex-1')
                ui.button('添加', on_click=add_userid, icon='add', color='primary')
            with ui.row().classes('w-full gap-2'):
                input_userid_del = ui.input('删除 UserID').props('outlined').classes('flex-1')
                ui.button('删除', on_click=delete_userid, icon='delete', color='red')
            with ui.row().classes('w-full justify-end'):
                ui.button('清空全部', on_click=clear_all, icon='delete_sweep', color='dark').props('flat')

            table_container = ui.column().classes('w-full gap-0')
            page_info = ui.label('').classes('text-sm text-gray-500')
            paginator = ui.pagination(1, 1).props('boundary-numbers')
            paginator.on('update:model-value', lambda e: load_data(int(e.args) if e.args else 1))

    ui.timer(0.1, lambda: load_data(1), once=True)
