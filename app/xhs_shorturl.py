import httpx
import json
from nicegui import app, ui
from xhshow import Xhshow

XHS_API_URL = 'https://edith.xiaohongshu.com/api/sns/web/short_url'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'

xhshow_client = Xhshow()


def ensure_cookie_with_a1(cookie_str: str) -> str:
    cookies = {}
    for part in cookie_str.split(';'):
        if '=' in part:
            key, value = part.strip().split('=', 1)
            cookies[key] = value
    if 'a1' not in cookies:
        cookies['a1'] = Xhshow.generate_a1()
    return '; '.join(f'{k}={v}' for k, v in cookies.items())


async def generate_short_url_backend(long_url: str, user_cookie: str) -> str:
    params_as_json_string = json.dumps({'applink': long_url})
    final_original_url_value = f'xhsdiscover://open_app?params={params_as_json_string}'
    payload_for_xhs = {'original_url': final_original_url_value}

    try:
        cookie_with_a1 = ensure_cookie_with_a1(user_cookie)
        sign_headers = xhshow_client.sign_headers_post(
            uri=XHS_API_URL,
            cookies=cookie_with_a1,
            payload=payload_for_xhs,
        )
    except Exception as e:
        raise Exception(f"第一步 [本地生成签名] 失败: {e}")

    xhs_api_headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': USER_AGENT,
        'cookie': cookie_with_a1,
        **sign_headers,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            xhs_response = await client.post(XHS_API_URL, json=payload_for_xhs, headers=xhs_api_headers)
            xhs_response.raise_for_status()
            xhs_response_data = xhs_response.json()
    except httpx.HTTPStatusError as e:
        raise Exception(f"第二步 [生成短链接] 失败 (HTTP {e.response.status_code})。\n响应详情: {e.response.text}")
    except Exception as e:
        raise Exception(f"第二步 [生成短链接] 时发生网络或解析错误: {e}")

    short_url = xhs_response_data.get('data', {}).get('short_url')
    if not short_url:
        raise Exception(f"第二步 [生成短链接] 失败: 未能提取 short_url。\n原始响应: {xhs_response_data}")

    return short_url if short_url.startswith('http') else 'https://' + short_url


def create_ui():
    COOKIE_STORAGE_KEY = 'xhs_shortlink_user_cookie'

    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-rose-500 to-red-500 rounded-t-2xl px-4 py-3'):
            ui.icon('link', size='28px').classes('text-white')
            ui.label('小红书短链接生成器').classes('text-xl font-bold text-white')

        with ui.column().classes('w-full gap-4 px-4 py-4'):
            url_input = ui.input(label='长链接', placeholder='例如: https://www.qq.com').props('outlined').classes('w-full')

            cookie_input = ui.textarea(label='Cookie (自动保存)') \
                .props('outlined').classes('w-full h-32') \
                .bind_value(app.storage.client, COOKIE_STORAGE_KEY)

            with ui.card().classes('w-full border-2') as result_card:
                result_html = ui.html().classes('w-full p-2')

            result_card.set_visibility(False)

            async def handle_generate():
                long_url = url_input.value
                cookie = cookie_input.value

                if not all([long_url, cookie]):
                    ui.notify('长链接和Cookie均不能为空！', color='negative')
                    return

                submit_btn.disable()
                submit_btn.text = '正在生成...'

                result_card.set_visibility(True)
                result_card.classes(remove='border-green-500 border-red-500', add='border-blue-500')
                result_html.content = '<strong>正在请求... (步骤 1/2: 本地生成签名)</strong>'

                try:
                    final_url = await generate_short_url_backend(long_url, cookie)
                    result_card.classes(remove='border-blue-500 border-red-500', add='border-green-500')
                    result_html.content = f'''
                        <strong>生成成功！短链接:</strong><br>
                        <input type="text" value="{final_url}" readonly 
                               onclick="navigator.clipboard.writeText(this.value).then(() => NiceGUI.notify('已复制到剪贴板！', {{color: 'positive'}})).catch(err => NiceGUI.notify('复制失败', {{color: 'negative'}}));" 
                               class="w-full mt-1 p-2 border rounded bg-gray-100 cursor-pointer">
                    '''
                except Exception as e:
                    result_card.classes(remove='border-blue-500 border-green-500', add='border-red-500')
                    result_html.content = f'<strong>错误：</strong><pre class="text-xs whitespace-pre-wrap break-all mt-1">{e}</pre>'
                finally:
                    submit_btn.enable()
                    submit_btn.text = '生成短链接'

            submit_btn = ui.button('生成短链接', on_click=handle_generate, icon='auto_awesome', color='red').classes('w-full')
