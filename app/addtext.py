import asyncio
from nicegui import ui
import config
from database import connect_to_mongo, close_mongo_connection
from devices.data import get_collection


def create_ui():
    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-green-600 to-emerald-600 rounded-t-2xl px-4 py-3'):
            ui.icon('rate_review', size='28px').classes('text-white')
            ui.label('文字消息').classes('text-xl font-bold text-white')
            ui.space()
        with ui.column().classes('w-full gap-4 px-4 py-4'):
            ui.label('管理私信文本内容').classes('text-lg font-bold text-green-600 dark:text-green-300')
            ui.label('多消息自动轮询，自动文本加噪。').classes('text-xs text-gray-400 -mt-1 ml-1')

            state = {'page': 1, 'page_size': 20, 'items': []}

            async def load_data(page: int = 1):
                state['page'] = page
                col = get_collection(config.MONGO_SEND_TEXT_COLLECTION)
                total = col.count_documents({})
                total_pages = max(1, (total + state['page_size'] - 1) // state['page_size'])
                state['page'] = max(1, min(page, total_pages))
                skip = (state['page'] - 1) * state['page_size']
                cursor = col.find({}).sort('_id', 1).skip(skip).limit(state['page_size'])
                items = []
                for doc in cursor:
                    items.append({'text': doc.get('text', '')})
                state['items'] = items
                table_container.clear()
                with table_container:
                    if not items:
                        ui.label('暂无文本消息').classes('text-gray-400 text-center w-full py-4')
                    for it in items:
                        with ui.row().classes('w-full items-center no-wrap gap-2 px-2 py-2 border-b border-gray-200 dark:border-gray-700'):
                            ui.label(it['text']).classes('flex-1 break-all')
                page_info.text = f'第 {state["page"]} / {total_pages} 页，共 {total} 条'
                paginator.max = total_pages
                paginator.set_value(state['page'])
                paginator.set_visibility(total_pages > 1)

            async def add_text():
                val = input_text.value.strip()
                if not val:
                    ui.notify('请输入文本内容！', color='warning')
                    return
                col = get_collection(config.MONGO_SEND_TEXT_COLLECTION)
                col.insert_one({'text': val})
                input_text.value = ''
                ui.notify('添加成功！', color='positive')
                await load_data(state['page'])

            async def delete_text():
                val = input_text_del.value.strip()
                if not val:
                    ui.notify('请输入要删除的文本！', color='warning')
                    return
                col = get_collection(config.MONGO_SEND_TEXT_COLLECTION)
                result = col.delete_many({'text': val})
                ui.notify(f'已删除 {result.deleted_count} 条', color='positive' if result.deleted_count else 'warning')
                input_text_del.value = ''
                await load_data(state['page'])

            async def clear_all():
                with ui.dialog() as dialog, ui.card().classes('rounded-2xl p-6'):
                    ui.icon('warning', size='48px').classes('text-red-500 self-center')
                    ui.label('确定清空所有文本？此操作不可撤销！').classes('text-lg font-bold self-center')
                    with ui.row().classes('w-full justify-end mt-4'):
                        ui.button('取消', on_click=dialog.close, color='gray')
                        ui.button('清空', on_click=lambda: dialog.submit('yes'), color='red')
                if await dialog == 'yes':
                    col = get_collection(config.MONGO_SEND_TEXT_COLLECTION)
                    result = col.delete_many({})
                    ui.notify(f'已清空 {result.deleted_count} 条', color='positive')
                    await load_data(1)

            with ui.row().classes('w-full gap-2'):
                input_text = ui.input('添加文本').props('outlined').classes('flex-1')
                ui.button('添加', on_click=add_text, icon='add', color='primary')
            with ui.row().classes('w-full gap-2'):
                input_text_del = ui.input('删除文本').props('outlined').classes('flex-1')
                ui.button('删除', on_click=delete_text, icon='delete', color='red')
            with ui.row().classes('w-full justify-end'):
                ui.button('清空全部', on_click=clear_all, icon='delete_sweep', color='dark').props('flat')

            table_container = ui.column().classes('w-full gap-0')
            page_info = ui.label('').classes('text-sm text-gray-500')
            paginator = ui.pagination(1, 1).props('boundary-numbers')
            paginator.on('update:model-value', lambda e: load_data(int(e.args) if e.args else 1))

    ui.timer(0.1, lambda: load_data(1), once=True)
