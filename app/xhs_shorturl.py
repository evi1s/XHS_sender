import httpx
from nicegui import app, ui
import config

SHORT_URL_PATH = '/short-url'


def _server_base() -> str:
    base = config.PROXY_SERVER_URL
    for suffix in ('/execute-task', '/execute_task', '/health'):
        if suffix in base:
            base = base.split(suffix)[0]
    return base.rstrip('/')


async def generate_short_url_backend(long_url: str, user_cookie: str) -> str:
    url = _server_base() + SHORT_URL_PATH
    headers = {
        'X-API-Key': config.PROXY_API_KEY,
        'Content-Type': 'application/json',
    }
    payload = {'long_url': long_url, 'user_cookie': user_cookie}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        detail = ''
        try:
            detail = e.response.json().get('detail', e.response.text)
        except Exception:
            detail = e.response.text
        raise Exception(f"远程生成短链接失败 (HTTP {e.response.status_code}): {detail}")
    except Exception as e:
        raise Exception(f"远程生成短链接时发生网络或连接错误: {e}")

    if data.get('status') != 'success':
        raise Exception(f"远程生成短链接失败: {data.get('detail') or data}")
    short_url = data.get('short_url')
    if not short_url:
        raise Exception("远程返回中未包含 short_url")
    return short_url


def create_ui():
    COOKIE_STORAGE_KEY = 'xhs_shortlink_user_cookie'

    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-rose-500 to-red-500 rounded-t-2xl px-4 py-3'):
            ui.icon('link', size='28px').classes('text-white')
            ui.label('小红书短链接生成器').classes('text-xl font-bold text-white')

        with ui.column().classes('w-full gap-4 px-4 py-4'):
            url_input = ui.input(label='长链接', placeholder='例如: https://www.qq.com').props('outlined').classes('w-full')

            cookie_input = ui.textarea(label='填入电脑端Cookie (自动临时保存)') \
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
                result_html.content = '<strong>正在请求远程服务器生成短链接...</strong>'

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
