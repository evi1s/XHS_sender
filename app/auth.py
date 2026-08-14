import hashlib
from database import db
from config import MONGO_MEMBER_COLLECTION
SALT = "a_very_secret_and_unique_salt_for_your_application_!@#$%^"
def get_password_hash(password: str) -> str:
    """
    salt+SHA-256哈希值。
    """
    salted_password = password + SALT
    hashed = hashlib.sha256(salted_password.encode('utf-8')).hexdigest()
    return hashed

async def verify_user_credentials(username: str, plain_password: str) -> bool:
    """
    验证用户凭据 (salt+SHA-256)。

    Args:
        username: 用户输入的账号。
        plain_password: 用户输入的明文密码。

    Returns:
        有效，则返回 True，否则返回 False。
    """
    if not username or not plain_password:
        return False

    try:
        member_collection = db[MONGO_MEMBER_COLLECTION]
        user_doc = await member_collection.find_one({'username': username})

        if not user_doc:
            print(f"验证失败: 用户 '{username}' 不存在。")
            return False

        stored_hashed_password = user_doc.get('password')
        if not stored_hashed_password:
            print(f"验证失败: 用户 '{username}' 没有设置密码。")
            return False

        input_hashed_password = get_password_hash(plain_password)

        is_valid = (input_hashed_password == stored_hashed_password)

        if is_valid:
            print(f"用户 '{username}' 验证成功。")
        else:
            print(f"验证失败: 用户 '{username}' 的密码错误。")

        return is_valid

    except Exception as e:
        print(f"验证过程中发生数据库错误: {e}")
        return False
