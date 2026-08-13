import asyncio
from typing import Dict
from bson.objectid import ObjectId
import math
from nicegui import ui
from devices.data import get_collection
from config import MONGO_USER_ID_COLLECTION


def add_user_ids_backend(user_ids_input: str) -> Dict[str, str]:
    """将多个 User ID 添加到 MongoDB 中。"""
    collection_name = MONGO_USER_ID_COLLECTION
    user_ids = [
        line.strip() for line in user_ids_input.strip().splitlines() if line.strip()
    ]
    if not user_ids:
        return {'status': 'error', 'message': '没有提供有效的 UserID。'}
    documents_to_insert = [{'user_id': uid} for uid in user_ids]
    try:
        collection = get_collection(collection_name)
        result = collection.insert_many(documents_to_insert)
        inserted_count = len(result.inserted_ids)
        return {
            'status': 'success',
            'message': f"成功向 Collection '{collection_name}' 插入了 {inserted_count} 个 User ID。"
        }
    except Exception as e:
        return {'status': 'error', 'message': f"数据库操作失败: {e}"}


def get_user_ids_paginated_backend(page: int, page_size: int = 10) -> Dict:
    """分页获取 User ID 列表。"""
    try:
        collection = get_collection(MONGO_USER_ID_COLLECTION)
        total_count = collection.count_documents({})
        if total_count == 0:
            return {'items': [], 'total_pages': 0}
        skip_amount = (page - 1) * page_size
        cursor = collection.find({}).skip(skip_amount).limit(page_size)
        items = [
            {'id': str(doc['_id']), 'user_id': doc.get('user_id', 'N/A')}
            for doc in cursor
        ]
        total_pages = math.ceil(total_count / page_size)
        return {'items': items, 'total_pages': total_pages}
    except Exception as e:
        print(f"Error fetching user IDs: {e}")
        return {'items': [], 'total_pages': 0, 'error': str(e)}


def delete_user_id_by_id_backend(doc_id: str) -> Dict:
    """根据文档的 _id 删除单个 User ID。"""
    try:
        collection = get_collection(MONGO_USER_ID_COLLECTION)
        result = collection.delete_one({'_id': ObjectId(doc_id)})
        if result.deleted_count > 0:
            return {'status': 'success', 'message': 'User ID 已删除。'}
        else:
            return {'status': 'error', 'message': '删除失败：未找到该 User ID。'}
    except Exception as e:
        return {'status': 'error', 'message': f"删除操作失败: {e}"}


def delete_all_user_ids_backend() -> Dict:
    """清空整个 User ID 集合。"""
    try:
        collection_name = MONGO_USER_ID_COLLECTION
        collection = get_collection(collection_name)
        result = collection.delete_many({})
        return {
            'status': 'success',
            'message': f"操作成功！已从集合 '{collection_name}' 中清空 {result.deleted_count} 条数据。"
        }
    except Exception as e:
        return {'status': 'error', 'message': f"清空操作失败: {e}"}


def create_ui():
    """UserId 管理界面"""

    async def load_data(page: int = 1):
        result = await asyncio.to_thread(get_user_ids_paginated_backend, page=page)
        if 'error' in result:
            ui.notify(f"加载数据失败: {result['error']}", color='negative')
            table.rows = []
            return

        table.rows = result['items']
        pagination.set_value(page)
        pagination.max = result['total_pages']
        pagination.set_visibility(result['total_pages'] > 1)

    async def perform_clear_all():
        dialog.close()
        ui.notify('正在清空所有数据...', spinner=True, timeout=2000)
        result = await asyncio.to_thread(delete_all_user_ids_backend)
        ui.notify(result['message'], color='positive' if result['status'] == 'success' else 'negative')
        await load_data()

    with ui.dialog() as dialog, ui.card().classes('rounded-2xl p-6'):
        ui.icon('warning', size='48px').classes('text-red-500 self-center')
        ui.label('确认要清空所有 User ID 吗？').classes('text-lg font-bold self-center')
        ui.label('此操作不可撤销！').classes('text-red-500 font-bold self-center')
        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('取消', on_click=dialog.close, color='grey')
            ui.button('确认清空', on_click=perform_clear_all, color='red', icon='delete_sweep')

    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-amber-500 to-orange-500 rounded-t-2xl px-4 py-3'):
            ui.icon('group_add', size='28px').classes('text-white')
            ui.label('UserId 管理').classes('text-xl font-bold text-white')

        with ui.expansion('添加 User ID', icon='add_circle', value=False).classes('w-full mt-2').props('header-class="text-primary"'):
            with ui.card_section():
                ui.label('添加私信接收方的Userid，userid在小红书作品和评论中获取。').classes('text-sm text-gray-500')
                ids_textarea = ui.textarea(label='User ID (每行一个)', placeholder='user_id_001\n...').props('outlined').classes('w-full h-48')

                async def handle_submit():
                    if not ids_textarea.value:
                        ui.notify('User ID 不能为空！', color='warning'); return
                    result = await asyncio.to_thread(add_user_ids_backend, ids_textarea.value)
                    if result['status'] == 'success':
                        ui.notify(result['message'], color='positive', multi_line=True)
                        ids_textarea.value = ''
                        await load_data()
                    else:
                        ui.notify(result['message'], color='negative', multi_line=True)

                ui.button('提交', on_click=handle_submit, icon='check', color='primary').classes('mt-2 w-full')

        ui.separator().classes('my-4')

        with ui.row().classes('w-full items-center justify-between px-2'):
            ui.label('管理 User ID').classes('text-lg font-bold text-amber-600 dark:text-amber-300')
            with ui.row().classes('gap-2'):
                ui.button('刷新列表', on_click=lambda: load_data(page=pagination.value), icon='refresh').props('flat dense')
                ui.button('清空所有', on_click=dialog.open, color='red', icon='delete_sweep').props('dense')

        columns = [
            {'name': 'user_id', 'label': 'User ID', 'field': 'user_id', 'align': 'left'},
            {'name': 'actions', 'label': '操作', 'align': 'center', 'style': 'width: 100px'},
        ]
        table = ui.table(columns=columns, rows=[], row_key='id').classes('h-96 w-full rounded-lg')
        pagination = ui.pagination(min=1, max=1, direction_links=True).bind_visibility_from(table, 'rows', backward=lambda rows: bool(rows))

        async def delete_single_id(doc_id: str):
            result = await asyncio.to_thread(delete_user_id_by_id_backend, doc_id)
            ui.notify(result['message'], color='positive' if result['status'] == 'success' else 'negative')
            current_page = pagination.value
            if len(table.rows) == 1 and current_page > 1:
                current_page -= 1
            await load_data(page=current_page)

        table.add_slot('body-cell-actions', '''
            <q-td :props="props">
                <q-btn flat dense round color="red" icon="delete" @click="() => $parent.$emit('delete', props.row.id)" />
            </q-td>
        ''')
        table.on('delete', lambda e: delete_single_id(e.args))
        pagination.on('update:model-value', lambda e: load_data(page=e.args))

        ui.timer(0.1, load_data, once=True)
