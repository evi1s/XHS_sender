import json
import requests
import config

def generate_short_url(long_url: str) -> str:
    try:
        api_url = config.PROXY_SERVER_URL.replace('/execute-task', '/short-url')
        resp = requests.post(api_url, json={'url': long_url}, headers={'X-API-Key': config.PROXY_API_KEY}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get('code') == 0:
            return data['data']['short_url']
        raise Exception(data.get('msg', '生成失败'))
    except Exception as e:
        raise Exception(f"短链接生成失败: {e}")
