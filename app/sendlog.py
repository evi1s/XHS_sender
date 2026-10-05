import asyncio
import math
from typing import Dict
from nicegui import ui
from devices.data import get_collection
import config


def _log_collection():
    """发送日志集合（名称取 config，缺省 sendlog）。"""
    return get_collection(getattr(config, 'MONGO_SEND_LOG_COLLECTION', 'sendlog'))


def get_logs_paginated_backend(page: int, page_size: int = 20) -> Dict:
    """分页获取发送日志（按时间倒序）。"""
    try:
        col = _log_collection()
        total_count = col.count_documents({})
        if total_count == 0:
            return {'items': [], 'total_pages': 0, 'total': 0, 'success': 0, 'failed': 0}

        skip_amount = (page - 1) * page_size
        cursor = col.find({}).sort([('_id', -1)]).skip(skip_amount).limit(page_size)

        docs = list(cursor)
        uids = {d.get('userid', '') for d in docs if d.get('userid')}
        nick_map = {}
        if uids:
            try:
                device_col = get_collection(config.MONGO_DEVICE_COLLECTION)
                for dev in device_col.find({'userid': {'$in': list(uids)}}, {'userid': 1, 'nickname': 1}):
                    nick_map[dev.get('userid')] = dev.get('nickname') or ''
            except Exception as e:
                print(f"Error fetching sender nicknames: {e}")

        items = []
        for doc in docs:
            text = doc.get('text', '') or ''
            reason = doc.get('reason', '') or ''
            userid = doc.get('userid', '') or ''
            nickname = doc.get('nickname') or nick_map.get(userid) or ''
            card_style = doc.get('card_style', '') or '无'
            if card_style == '无':
                card_style = '文本'
            items.append({
                'id': str(doc['_id']),
                'time': doc.get('time', '') or '',
                'userid': userid,
                'nickname': nickname or userid or '-',
                '_showId': False,
                'receiver_id': doc.get('receiver_id', '') or '-',
                'text': text if text else '-',
                'send_mode': doc.get('send_mode', '') or '',
                'card_style': card_style,
                'status': doc.get('status', '') or '',
                'reason': reason if reason else '-',
                'detail': doc.get('detail', '') or '',
            })

        return {
            'items': items,
            'total_pages': math.ceil(total_count / page_size),
            'total': total_count,
            'success': col.count_documents({'status': '成功'}),
            'failed': col.count_documents({'status': '失败'}),
        }
    except Exception as e:
        print(f"Error fetching send logs: {e}")
        return {'items': [], 'total_pages': 0, 'error': str(e)}


def create_send_log_ui():
    """私信发送日志界面"""

    async def load_data(page: int = 1):
        result = await asyncio.to_thread(get_logs_paginated_backend, page=page)
        if 'error' in result:
            ui.notify(f"加载数据失败: {result['error']}", color='negative')
            table.rows = []
            return

        table.rows = result['items']
        pagination.set_value(page)
        pagination.max = result['total_pages'] or 1
        pagination.set_visibility((result['total_pages'] or 0) > 1)

        total = result.get('total', 0)
        success = result.get('success', 0)
        failed = result.get('failed', 0)
        summary.set_text(f'共 {total} 条 · 成功 {success} · 失败 {failed}')

    with ui.card().classes('w-full max-w-6xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-sky-500 to-blue-600 rounded-t-2xl px-4 py-3'):
            ui.icon('receipt_long', size='28px').classes('text-white')
            ui.label('私信发送日志').classes('text-xl font-bold text-white')

        with ui.row().classes('w-full items-center justify-between px-2 mt-2'):
            summary = ui.label('加载中...').classes('text-sm text-gray-500')
            with ui.row().classes('gap-2'):
                ui.button('刷新列表', on_click=lambda: load_data(page=pagination.value), icon='refresh').props('flat dense')

        columns = [
            {'name': 'time', 'label': '发送时间', 'field': 'time', 'align': 'left', 'style': 'width: 150px'},
            {'name': 'userid', 'label': '发送账号', 'field': 'userid', 'align': 'left', 'style': 'width: 150px'},
            {'name': 'receiver_id', 'label': '接收方', 'field': 'receiver_id', 'align': 'left', 'style': 'width: 150px'},
            {'name': 'text', 'label': '文字内容', 'field': 'text', 'align': 'left', 'style': 'white-space: normal; max-width: 240px;'},
            {'name': 'card_style', 'label': '卡片样式', 'field': 'card_style', 'align': 'center', 'style': 'width: 110px'},
            {'name': 'status', 'label': '状态', 'field': 'status', 'align': 'center', 'style': 'width: 80px'},
            {'name': 'reason', 'label': '失败原因', 'field': 'reason', 'align': 'left', 'style': 'white-space: normal; max-width: 220px;'},
        ]
        table = ui.table(columns=columns, rows=[], row_key='id').classes('w-full rounded-lg')
        pagination = ui.pagination(min=1, max=1, direction_links=True).bind_visibility_from(table, 'rows', backward=lambda rows: bool(rows))

        table.add_slot('body-cell-userid', '''
            <q-td :props="props">
                <span style="cursor: pointer; text-decoration: underline dotted;"
                      :title="props.row._showId ? '点击显示昵称' : '点击显示账号ID'"
                      @click="props.row._showId = !props.row._showId">
                    {{ props.row._showId ? props.row.userid : props.row.nickname }}
                </span>
            </q-td>
        ''')
        table.add_slot('body-cell-status', '''
            <q-td :props="props">
                <q-badge :color="props.value === '成功' ? 'green' : 'red'" :label="props.value" />
            </q-td>
        ''')
        table.add_slot('body-cell-reason', '''
            <q-td :props="props">
                <span :title="props.row.detail">{{ props.value }}</span>
            </q-td>
        ''')
        pagination.on('update:model-value', lambda e: load_data(page=e.args))

        ui.timer(0.1, load_data, once=True)
