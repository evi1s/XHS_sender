from datetime import datetime, timezone
import re


def extract_xhs_user_id(text: str) -> str:
    """
    从完整链接或原始字符串中提取小红书用户ID。
    """
    m = re.search(r'/user/profile/([0-9a-fA-F]{24})', text)
    if m:
        return m.group(1)

    text = text.strip()
    if re.fullmatch(r'[0-9a-fA-F]{24}', text):
        return text

    raise ValueError('未找到合法的 24 位十六进制用户 ID')


def objectid_to_datetime(object_id: str) -> datetime:
    """
    按 MongoDB ObjectId 规则解析前 8 位时间戳。
    """
    if not re.fullmatch(r'[0-9a-fA-F]{24}', object_id):
        raise ValueError('ObjectId 必须是 24 位十六进制字符串')

    ts_hex = object_id[:8]
    ts = int(ts_hex, 16)
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def convert_xhs_register_time(text: str):
    user_id = extract_xhs_user_id(text)
    dt_utc = objectid_to_datetime(user_id)
    dt_local = dt_utc.astimezone()
    return {
        'user_id': user_id,
        'utc_time': dt_utc.strftime('%Y-%m-%d %H:%M:%S'),
        'local_time': dt_local.replace(tzinfo=None).strftime('%Y-%m-%d %H:%M:%S'),
    }
