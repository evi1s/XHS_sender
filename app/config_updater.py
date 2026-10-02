import re
import os
from threading import Lock

file_lock = Lock()

def update_config_file(key: str, value: str) -> dict:
    """
    动态更新配置文件中的一个变量值。


    Args:
        key (str): 要更新的变量名。
        value (str): 要设置的新值。

    Returns:
        dict: 一个包含操作状态和消息的字典。
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config.py')

    if not os.path.exists(config_path):
        return {'status': 'error', 'message': f"配置文件 {config_path} 未找到！"}

    with file_lock:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            pattern = re.compile(r"^(%s\s*=\s*)(['\"])?.*(['\"])?\s*$" % re.escape(key))
            
            new_lines = []
            found = False
            for line in lines:
                if pattern.match(line):
                    new_line = f"{key} = '{value}'\n"
                    new_lines.append(new_line)
                    found = True
                else:
                    new_lines.append(line)

            if not found:
                return {'status': 'error', 'message': f"在 config.py 中未找到变量 {key}。"}

            with open(config_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            return {'status': 'success', 'message': f"config.py 已更新：{key} 设置为 {value}"}

        except Exception as e:
            return {'status': 'error', 'message': f"更新 config.py 失败: {e}"}