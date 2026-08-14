import hashlib
import time
import uuid
from datetime import datetime
import pytz


def generate_xhs_fingerprint(did: str) -> str:
    if not did:
        return ""
    shanghai_tz = pytz.timezone('Asia/Shanghai')
    timestamp = datetime.now(shanghai_tz).strftime('%Y%m%d%H%M%S')
    md5_did = hashlib.md5(did.encode()).hexdigest()
    key = f"{timestamp}{md5_did}00"
    in_str = f"shumei_ios_sec_key_{key}"
    md5_fragment = hashlib.md5(in_str.encode()).hexdigest()[:14]
    return f"{key}{md5_fragment}"


def generate_xhs_fid() -> str:
    timestamp = int(time.time())
    md5_uuid = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()
    return f"{timestamp}-0-0-{md5_uuid}"
