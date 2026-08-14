import os
from nicegui import ui
import httpx
import json

XHS_API_URL = 'https://edith.xiaohongshu.com/api/sns/octopus/router/longlinkconfig'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
COOKIE_STORAGE_KEY = 'xhs_shortlink_user_cookie'


def create_ui():
    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-rose-600 to-pink-600 rounded-t-2xl px-4 py-3'):
            ui.icon('link', size='28px').classes('text-white')
            ui.label('短链生成').classes('text-xl font-bold text-white')
            ui.space()
        with ui.column().classes('w-full gap-4 px-4 py-4'):
            ui.label('生成小红书商品短链接').classes('text-lg font-bold')
            ui.label('粘贴商品链接或商品 ID，生成可发送的短链接。').classes('text-sm text-gray-500')

            input_url = ui.input('商品链接或 ID', placeholder='粘贴完整链接或商品ID').props('outlined').classes('w-full')
            result_card = ui.card().classes('w-full rounded-xl border mt-2')
            result_html = ui.html('')

            async def handle_generate():
                val = input_url.value.strip()
                if not val:
                    ui.notify('请输入链接或 ID！', color='warning')
                    return
                submit_btn.disable()
                submit_btn.text = '生成中...'
                try:
                    async with httpx.AsyncClient(timeout=15) as client:
                        headers = {'User-Agent': USER_AGENT}
                        payload = {'url': val}
                        xhs_response = await client.post(XHS_API_URL, json=payload, headers=headers)
                        xhs_response.raise_for_status()
                        xhs_response_data = xhs_response.json()
                        if xhs_response_data.get('code') != 0:
                            raise Exception(f"生成失败: {xhs_response_data.get('msg', '未知错误')}")
                        short_url = xhs_response_data.get('data', {}).get('short_url', '')
                        if not short_url:
                            raise Exception("未能提取短链接")
                        result_card.classes(remove='border-red-500', add='border-green-500')
                        result_html.content = f'''
                        <div class="p-3">
                            <strong>短链接：</strong><br>
                            <input type="text" value="{short_url}" readonly
                                   onclick="navigator.clipboard.writeText(this.value).then(() => NiceGUI.notify('已复制到剪贴板！', {{color: 'positive'}})).catch(err => NiceGUI.notify('复制失败', {{color: 'negative'}}));"
                                   class="w-full mt-1 p-2 border rounded bg-gray-100 cursor-pointer">
                        </div>
                        '''
                except Exception as e:
                    result_card.classes(remove='border-green-500', add='border-red-500')
                    result_html.content = f'<strong>错误：</strong><pre class="text-xs whitespace-pre-wrap break-all mt-1">{e}</pre>'
                finally:
                    submit_btn.enable()
                    submit_btn.text = '生成短链接'

            submit_btn = ui.button('生成短链接', on_click=handle_generate, icon='auto_awesome', color='red').classes('w-full')
