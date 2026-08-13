from bson.objectid import ObjectId
from typing import Optional, Dict
from devices.data import get_devices_collection
from devices.readdate import convert_xhs_register_time


def get_all_devices_summary() -> list:
    """获取所有设备的摘要列表。"""
    devices_collection = get_devices_collection()
    devices = devices_collection.find({}, {'nickname': 1, 'userid': 1})

    summary_list = [
        {
            'value': str(d['_id']),
            'label': f"{d.get('nickname', 'N/A')} (ID: {d.get('userid', 'N/A')})"
        }
        for d in devices
    ]
    return summary_list


def get_all_devices_list() -> list:
    """获取所有设备的列表数据，用于分页展示。"""
    devices_collection = get_devices_collection()
    devices = devices_collection.find(
        {},
        {
            'nickname': 1,
            'userid': 1,
            'next_send_time': 1,
            'consecutive_fail_days': 1,
            'remarks': 1,
        },
    ).sort('nickname', 1)

    result = []
    for d in devices:
        userid = d.get('userid', 'N/A')
        register_time = ''
        try:
            register_time = convert_xhs_register_time(userid).get('local_time', '')
        except Exception:
            register_time = ''

        result.append({
            '_id': str(d.get('_id', '')),
            'nickname': d.get('nickname', 'N/A'),
            'userid': userid,
            'register_time': register_time,
            'next_send_time': d.get('next_send_time', ''),
            'consecutive_fail_days': d.get('consecutive_fail_days', 0),
            'remarks': d.get('remarks', ''),
        })
    return result


def get_device_by_id(device_id: str) -> Optional[Dict]:
    """根据ID获取单个设备的详细信息。"""
    try:
        devices_collection = get_devices_collection()
        device = devices_collection.find_one({'_id': ObjectId(device_id)})
        if device and '_id' in device:
            device['_id'] = str(device['_id'])
        return device
    except Exception as e:
        print(f"Error getting device by ID '{device_id}': {e}")
        return None


def add_or_update_device(data: Dict) -> Dict:
    """添加或更新设备信息。"""
    devices_collection = get_devices_collection()
    device_id_str = data.pop('_id', None)

    try:
        if device_id_str:
            device_id = ObjectId(device_id_str)
            result = devices_collection.update_one({'_id': device_id}, {'$set': data})
            if result.matched_count > 0:
                return {'status': 'success', 'message': f"设备 {data.get('nickname')} 更新成功！"}
            return {'status': 'error', 'message': f"更新失败：未找到ID为 {device_id_str} 的设备。"}
        result = devices_collection.insert_one(data)
        return {'status': 'success', 'message': f"新设备 {data.get('nickname')} 添加成功！ (ID: {result.inserted_id})"}
    except Exception as e:
        return {'status': 'error', 'message': f"保存失败: {e}"}


def delete_device(device_id: str) -> Dict:
    """根据ID删除设备。"""
    try:
        devices_collection = get_devices_collection()
        result = devices_collection.delete_one({'_id': ObjectId(device_id)})
        if result.deleted_count > 0:
            return {'status': 'success', 'message': '设备已成功删除。'}
        return {'status': 'error', 'message': '删除失败：未找到该设备。'}
    except Exception as e:
        return {'status': 'error', 'message': f"删除失败: {e}"}
