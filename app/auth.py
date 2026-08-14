import re
import hashlib
import config

SALT = "a_very_secret_and_unique_salt_for_your_application_!@#$%^"

def authenticate(username: str, password: str) -> bool:
    if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
        return True
    return False

def hash_password(password: str) -> str:
    salted = SALT + password
    return hashlib.sha256(salted.encode()).hexdigest()
