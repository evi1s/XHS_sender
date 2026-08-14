import asyncio
from typing import Dict
from bson.objectid import ObjectId
import math
from nicegui import ui
from devices.data import get_collection
from config import MONGO_COMMENT_COLLECTION


def add_comments_backend(comments_input: str) -> Dict[str, str]:
    """将多条私信文本内容添加到 MongoDB 中。"""
    collection_name = MONGO_COMMENT_COLLECTION
    comments = [
        line.strip() for line in comments_input.strip().splitlines() if line.strip()
    ]
    if not comments:
        return {'status': 'error', 'message': '没有提供有效的私信内容。'}

    documents_to_insert = [{'text': comment} for comment in comments]
    try:
        collection = get_collection(collection_name)
        result = collection.insert_many(documents_to_insert)
        inserted_count = len(result.inserted_ids)
        return {
            'status': 'success',
            'message': f"成功向 Collection '{collection_name}' 插入了 {inserted_count} 条私信文本。"
        }
    except Exception as e:
        return {'status': 'error', 'message': f"数据库操作失败: {e}"}


def get_comments_paginated_backend(page: int, page_size: int = 10) -> Dict:
    """分页获取私信文本列表。"""
    try:
        collection = get_collection(MONGO_COMMENT_COLLECTION)
        total_count = collection.count_documents({})
        if total_count == 0:
            return {'items': [], 'total_pages': 0}

        skip_amount = (page - 1) * page_size
        cursor = collection.find({}).skip(skip_amount).limit(page_size)

        items = [
            {'id': str(doc['_id']), 'text': doc.get('text', 'N/A')}
            for doc in cursor
        ]
        total_pages = math.ceil(total_count / page_size)
        return {'items': items, 'total_pages': total_pages}
    except Exception as e:
        print(f"Error fetching comments: {e}")
        return {'items': [], 'total_pages': 0, 'error': str(e)}


def delete_comment_by_id_backend(doc_id: str) -> Dict:
    """根据文档的 _id 删除单条私信文本。"""
    try:
        collection = get_collection(MONGO_COMMENT_COLLECTION)
        result = collection.delete_one({'_id': ObjectId(doc_id)})
        if result.deleted_count > 0:
            return {'status': 'success', 'message': '评论已删除。'}
        else:
            return {'status': 'error', 'message': '删除失败：未找到该私信文本。'}
    except Exception as e:
        return {'status': 'error', 'message': f"删除操作失败: {e}"}


def delete_all_comments_backend() -> Dict:
    """清空整个私信文本集合。"""
    try:
        collection_name = MONGO_COMMENT_COLLECTION
        collection = get_collection(collection_name)
        result = collection.delete_many({})
        return {
            'status': 'success',
            'message': f"操作成功！已从集合 '{collection_name}' 中清空 {result.deleted_count} 条数据。"
        }
    except Exception as e:
        return {'status': 'error', 'message': f"清空操作失败: {e}"}


def create_ui():
    """文字消息管理界面"""

    async def load_data(page: int = 1):
        result = await asyncio.to_thread(get_comments_paginated_backend, page=page)
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
        ui.notify('正在清空所有私信文本...', spinner=True, timeout=2000)
        result = await asyncio.to_thread(delete_all_comments_backend)
        ui.notify(result['message'], color='positive' if result['status'] == 'success' else 'negative')
        await load_data()

    with ui.dialog() as dialog, ui.card().classes('rounded-2xl p-6'):
        ui.icon('warning', size='48px').classes('text-red-500 self-center')
        ui.label('确认要清空所有私信内容吗？').classes('text-lg font-bold self-center')
        ui.label('此操作不可撤销！').classes('text-red-500 font-bold self-center')
        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('取消', on_click=dialog.close, color='grey')
            ui.button('确认清空', on_click=perform_clear_all, color='red', icon='delete_sweep')

    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-green-500 to-emerald-500 rounded-t-2xl px-4 py-3'):
            ui.icon('rate_review', size='28px').classes('text-white')
            ui.label('文字消息管理').classes('text-xl font-bold text-white')

        with ui.expansion('添加私信内容', icon='add_comment', value=False).classes('w-full mt-2').props('header-class="text-primary"'):
            with ui.card_section():
                ui.label('添加需要发送给对方的私信内容，为文本格式，尽量避免营销敏感词').classes('text-sm text-gray-500')
                textarea = ui.textarea(label='私信内容 (每行一条)', placeholder='你好，这是一条评论示例。\n另一条评论...') \
                    .props('outlined').classes('w-full h-48')

                async def handle_submit():
                    if not textarea.value:
                        ui.notify('评论内容不能为空！', color='warning'); return
                    result = await asyncio.to_thread(add_comments_backend, textarea.value)
                    if result['status'] == 'success':
                        ui.notify(result['message'], color='positive', multi_line=True)
                        textarea.value = ''
                        await load_data()
                    else:
                        ui.notify(result['message'], color='negative', multi_line=True)

                ui.button('提交', on_click=handle_submit, icon='check', color='primary').classes('mt-2 w-full')

        ui.separator().classes('my-4')

        with ui.row().classes('w-full items-center justify-between px-2'):
            ui.label('管理私信文本内容').classes('text-lg font-bold text-green-600 dark:text-green-300')
            ui.label('多消息自动轮询，自动文本加噪。').classes('text-xs text-gray-400 -mt-1 ml-1')
            with ui.row().classes('gap-2'):
                ui.button('刷新列表', on_click=lambda: load_data(page=pagination.value), icon='refresh').props('flat dense')
                ui.button('清空所有', on_click=dialog.open, color='red', icon='delete_sweep').props('dense')

        columns = [
            {'name': 'text', 'label': '私信内容', 'field': 'text', 'align': 'left', 'style': 'white-space: normal;'},
            {'name': 'actions', 'label': '操作', 'align': 'center', 'style': 'width: 100px'},
        ]
        table = ui.table(columns=columns, rows=[], row_key='id').classes('h-96 w-full rounded-lg')
        pagination = ui.pagination(min=1, max=1, direction_links=True).bind_visibility_from(table, 'rows', backward=lambda rows: bool(rows))

        async def delete_single_id(doc_id: str):
            result = await asyncio.to_thread(delete_comment_by_id_backend, doc_id)
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
