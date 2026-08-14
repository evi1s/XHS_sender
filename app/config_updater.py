import os

def update_config_file(key: str, value) -> dict:
    try:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.py')
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        new_lines = []
        updated = False
        pattern = key + ' '
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(key) and not stripped.startswith('#'):
                if isinstance(value, str):
                    new_lines.append(f"{key} = '{value}'\n")
                else:
                    new_lines.append(f"{key} = {value}\n")
                updated = True
            else:
                new_lines.append(line)
        if not updated:
            if isinstance(value, str):
                new_lines.append(f"{key} = '{value}'\n")
            else:
                new_lines.append(f"{key} = {value}\n")
        with open(config_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return {'status': 'success', 'message': f'配置项 {key} 已更新。'}
    except Exception as e:
        return {'status': 'error', 'message': f'更新配置失败: {e}'}
