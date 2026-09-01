import asyncio
from nicegui import ui
from typing import Dict
from . import utils, db_logic
import config
from config_updater import update_config_file
import importlib



def create_device_management_ui():


    ui.add_head_html('<style>.xy-ph .q-field__native::placeholder{opacity:1 !important;color:#9e9e9e !important;}</style>')
    state: Dict[str, any] = {}
    device_label_to_id_map = {}

    async def clear_form(reset_picker: bool = True):
        if 'doc_id_to_submit' in state: state['doc_id_to_submit'].value = ''
        for key in form_fields:
            if key in state and state[key]:
                state[key].value = ''
        if 'consecutive_failure_days' in state and state['consecutive_failure_days']:
            state['consecutive_failure_days'].value = ''
        state['platform'].value = 'iOS'
        state['save_button'].text = '添加新设备'
        state['delete_button'].set_visibility(False)
        state['original_next_send_time'] = ''
        if 'health_check_switch' in state and state['health_check_switch']:
            state['health_check_switch'].set_value(False)
        if reset_picker and 'device_picker' in state and state['device_picker']:
            state['device_picker'].value = None

    async def reload_device_list():
        ui.notify('正在刷新设备列表...', color='info')
        try:
            importlib.reload(config)
            device_list_of_dicts = await asyncio.to_thread(db_logic.get_all_devices_summary)
            nonlocal device_label_to_id_map
            device_label_to_id_map.clear()
            labels_for_display = [item['label'] for item in device_list_of_dicts]
            device_label_to_id_map = {item['label']: item['value'] for item in device_list_of_dicts}
            state['device_picker'].set_options(labels_for_display)
            ui.notify('设备列表已刷新。', color='positive')
        except Exception as e:
            ui.notify(f'加载设备列表失败: {e}', color='negative', multi_line=True)

    async def on_health_check_toggled(e):
        importlib.reload(config)

        current_userid = state['userid'].value
        if not current_userid:
            ui.notify('请先在表单中填写 UserID！', color='warning')
            state['health_check_switch'].set_value(False)
            return

        if e.value:
            if config.CHECK_USER_ID == current_userid:
                return

            result = await asyncio.to_thread(update_config_file, 'CHECK_USER_ID', current_userid)
            ui.notify(result['message'], color='positive' if result['status'] == 'success' else 'negative')
            if result['status'] == 'success':
                importlib.reload(config)
                state['next_send_time'].value = '2099-12-30T00:00'
                ui.notify('下次发送时间已锁定。', color='info')
            else:
                state['health_check_switch'].set_value(False)

        else:
            if config.CHECK_USER_ID == current_userid:
                result = await asyncio.to_thread(update_config_file, 'CHECK_USER_ID', "")
                ui.notify(result['message'], color='positive' if result['status'] == 'success' else 'negative')
                if result['status'] == 'success':
                    importlib.reload(config)
                    state['next_send_time'].value = (state.get('original_next_send_time', '') or '').replace(' ', 'T')[:16]
                    ui.notify('健康检测号已在配置文件中清空。', color='info')

    async def on_device_picked():
        selected_label = state['device_picker'].value
        if not selected_label:
            await clear_form(reset_picker=False)
            return
        picked_id = device_label_to_id_map.get(selected_label)
        if not picked_id:
            ui.notify(f'无法找到标签 "{selected_label}" 对应的ID。', color='negative'); return
        try:
            importlib.reload(config)
            device_data = await asyncio.to_thread(db_logic.get_device_by_id, picked_id)
            if device_data:
                state['doc_id_to_submit'].value = device_data.get('_id', '')
                for key in form_fields:
                    if key != 'next_send_time' and key in state and state[key]:
                        state[key].value = device_data.get(key, '')

                state['consecutive_failure_days'].value = device_data.get('consecutive_fail_days', 0)

                state['save_button'].text = '更新设备数据'
                state['delete_button'].set_visibility(True)
                original_time = device_data.get('next_send_time', '')
                state['original_next_send_time'] = original_time

                device_userid = device_data.get('userid')
                current_check_id = config.CHECK_USER_ID

                if device_userid and device_userid == current_check_id:
                    state['health_check_switch'].set_value(True)
                    state['next_send_time'].value = '2099-12-30T00:00'
                else:
                    state['health_check_switch'].set_value(False)
                    state['next_send_time'].value = original_time.replace(' ', 'T')[:16] if original_time else ''

                ui.notify('设备信息加载成功。', color='positive')
            else:
                ui.notify(f'加载设备 {picked_id} 失败！', color='negative')
        except Exception as e:
            ui.notify(f'处理设备数据时出错: {e}', color='negative', multi_line=True)

    def toggle_edit_mode():
        is_visible = not state['picker_row'].visible
        state['picker_row'].set_visibility(is_visible)
        state['toggle_button'].text = '返回添加新设备' if is_visible else '选择现有设备编辑'
        if not is_visible:
            ui.timer(0.1, lambda: clear_form(reset_picker=True), once=True)

    def generate_fingerprint():
        did = state['did'].value
        if not did: ui.notify('请先输入 DeciceID (did)', color='warning'); return
        state['fingerprint'].value = utils.generate_xhs_fingerprint(did)
        ui.notify('Fingerprint 已生成。', color='positive')

    def generate_fid():
        state['x_legacy_fid'].value = utils.generate_xhs_fid()
        ui.notify('X-Legacy-FID 已生成。', color='positive')

    async def save_device():
        if not (state['userid'].value and state['nickname'].value):
            ui.notify('User ID 和 Nickname 不能为空！', color='negative'); return
        data_to_save = {key: state[key].value for key in form_fields}
        if data_to_save.get('next_send_time'):
            t = data_to_save['next_send_time']
            data_to_save['next_send_time'] = t.replace('T', ' ') + ':00' if len(t) == 16 else t
        data_to_save['_id'] = state['doc_id_to_submit'].value

        ui.notify('正在保存...', color='info')
        result = await asyncio.to_thread(db_logic.add_or_update_device, data_to_save)
        ui.notify(result['message'], color='positive' if result['status'] == 'success' else 'info')
        await reload_device_list()
        if state['picker_row'].visible:
            toggle_edit_mode()
        else:
            await clear_form()

    async def delete_device():
        with ui.dialog() as dialog, ui.card().classes('rounded-2xl p-6'):
            ui.icon('delete_forever', size='48px').classes('text-red-500 self-center')
            ui.label('确定删除此设备吗？此操作不可撤销！').classes('text-lg font-bold self-center')
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('取消', on_click=dialog.close, color='gray')
                ui.button('删除', on_click=lambda: dialog.submit('yes'), color='red')
        result = await dialog
        if result == 'yes':
            device_id = state['doc_id_to_submit'].value
            if not device_id: return

            if state['userid'].value and state['userid'].value == config.CHECK_USER_ID:
                await asyncio.to_thread(update_config_file, 'CHECK_USER_ID', "")
                importlib.reload(config)
                ui.notify('被删除的设备是当前的健康检测号，配置已清空。', color='warning')

            ui.notify('删除中...', color='warning')
            delete_result = await asyncio.to_thread(db_logic.delete_device, device_id)
            ui.notify(delete_result['message'], color='positive' if delete_result['status'] == 'success' else 'negative')
            await reload_device_list()
            if state['picker_row'].visible:
                toggle_edit_mode()
            else:
                await clear_form()

    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-blue-600 to-indigo-600 rounded-t-2xl px-4 py-3'):
            ui.icon('devices_other', size='28px').classes('text-white')
            ui.label('小红书账号管理').classes('text-xl font-bold text-white')
            ui.space()
            ui.button(icon='refresh', on_click=reload_device_list, color='white').props('flat round text-color=primary').tooltip('刷新设备列表')

        with ui.column().classes('w-full gap-4 px-4 py-4'):
            state['doc_id_to_submit'] = ui.input(value='').style('display: none')
            state['original_next_send_time'] = ''

            with ui.row().classes('w-full items-center'):
                state['toggle_button'] = ui.button('选择现有设备进行编辑', on_click=toggle_edit_mode, icon='edit', color='secondary')

            picker_row_container = ui.row().classes('w-full')
            picker_row_container.set_visibility(False)
            with picker_row_container:
                state['picker_row'] = picker_row_container
                state['device_picker'] = ui.select([], label='选择一个现有设备', on_change=on_device_picked, clearable=True).classes('w-full')

            form_fields = ['nickname', 'userid', 'did', 'build', 'version', 'platform', 'xy-direction', 'session', 'x_legacy_fid', 'fingerprint', 'remarks', 'next_send_time']

            with ui.grid(columns=2).classes('gap-4 w-full'):
                state['nickname'] = ui.input('Nickname*').props('outlined')
                state['userid'] = ui.input('UserID*').props('outlined')
                state['did'] = ui.input('DeciceID').props('outlined')
                state['build'] = ui.input('Build').props('outlined')
                state['version'] = ui.input('Version').props('outlined')
                state['platform'] = ui.input('Platform', value='iOS').props('outlined')
                state['xy-direction'] = ui.input('XY-Direction').props('outlined placeholder=非必填').classes('xy-ph')
                state['session'] = ui.input('Session').props('outlined')

            with ui.row().classes('w-full items-center'):
                state['x_legacy_fid'] = ui.input('X-Legacy-FID').props('outlined').classes('flex-grow')
                ui.button('生成', on_click=generate_fid, color='secondary', icon='auto_fix_high')

            with ui.row().classes('w-full items-center'):
                state['fingerprint'] = ui.input('Fingerprint').props('outlined').classes('flex-grow')
                ui.button('生成', on_click=generate_fingerprint, color='secondary', icon='auto_fix_high')

            state['remarks'] = ui.textarea('备注 (Remarks)').props('outlined').classes('w-full')

            with ui.grid(columns=2).classes('w-full items-center gap-4'):
                with ui.row().classes('w-full items-center gap-4'):
                    state['next_send_time'] = ui.input('下次发送时间').props('outlined type=datetime-local step=60').classes('flex-grow')
                    state['consecutive_failure_days'] = ui.input('连续失败天数').props('readonly outlined').classes('flex-grow')
                with ui.row().classes('w-full items-center justify-start h-full'):
                    state['health_check_switch'] = ui.switch('健康检测号', on_change=on_health_check_toggled)

            with ui.row().classes('w-full mt-4 gap-2'):
                state['save_button'] = ui.button('添加新设备', on_click=save_device, icon='save', color='primary').classes('flex-grow')
                delete_button_instance = ui.button('删除当前设备', on_click=delete_device, color='red', icon='delete')
                delete_button_instance.set_visibility(False)
                state['delete_button'] = delete_button_instance

    ui.timer(0.2, reload_device_list, once=True)