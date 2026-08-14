import json
import os
from nicegui import ui
import config
import importlib

CARD_JSON_PATH = 'xhs3.json'


def load_card_json():
    try:
        if os.path.exists(CARD_JSON_PATH):
            with open(CARD_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f'加载卡片模板失败: {e}')
    return None


def save_card_json(data):
    with open(CARD_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent='\t')


def create_card_editor_ui():
    fields = {}

    def _add_field(key, label, placeholder=''):
        fields[key] = ui.input(label, placeholder=placeholder).props('outlined').classes('w-1/2')

    def refresh_preview():
        preview_html.content = _preview_card_html()

    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-indigo-600 to-purple-600 rounded-t-2xl px-4 py-3'):
            ui.icon('style', size='28px').classes('text-white')
            ui.label('卡片消息').classes('text-xl font-bold text-white')
            ui.space()
        with ui.row().classes('w-full px-4 py-4 gap-6'):
            with ui.column().classes('w-1/2 gap-2'):
                ui.label('标题与内容').classes('text-lg font-bold')
                _add_field('title', '卡片标题', '例如：快速精准引流，高效客户转化')
                _add_field('image', '卡片图片 URL', 'https://...')
                ui.label('显示信息位置').classes('text-lg font-bold mt-4')
                _add_field('user_name', '卖家昵称', '例如：薯队长推荐🔥')
                _add_field('avatar', '头像 URL', 'https://...')
                ui.label('显示信息位置').classes('text-lg font-bold mt-4')
                _add_field('tag', '标签文案', '例如：点击加微信详聊')
                ui.label('跳转链接').classes('text-lg font-bold mt-4')
                _add_field('link', '短链 URL', 'https://...')
                with ui.row().classes('w-full gap-2 mt-4'):
                    ui.button('保存到文件', on_click=save_to_disk, icon='save', color='primary')
                    ui.button('重新加载', on_click=load_json_content, icon='refresh', color='secondary')
            with ui.column().classes('w-80 justify-center items-center gap-2'):
                ui.label('👁️ 实时预览').classes('font-bold text-gray-500')
                with ui.column().classes('relative').style('width:330px;max-width:100%'):
                    preview_html = ui.html('').classes('w-full')
                    ui.image('/img/card_icon.jpeg').style(
                        'position:absolute;top:-12px;left:-6px;width:42px;height:42px;border-radius:50%;'
                        'z-index:10;border:2px solid #fff;box-shadow:0 2px 8px rgba(255,36,66,.45);'
                        'object-fit:cover;'
                    )

    def _preview_card_html() -> str:
        title = fields['title'].value or '标题'
        user_name = fields['user_name'].value or '昵称'
        tag = fields['tag'].value or '点击咨询'
        img_url = fields['image'].value or ''
        avatar_url = fields['avatar'].value or ''
        img_html = f'<img src="{img_url}" style="width:100%;height:100%;object-fit:cover;">' if img_url else '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#9ca3af;font-size:13px;">商品图片</div>'
        avatar_html = f'<img src="{avatar_url}" style="width:18px;height:18px;border-radius:50%;object-fit:cover;margin-right:4px;">' if avatar_url else ''
        return f'''
        <div style="position:relative;width:330px;max-width:100%;">
            <div style="width:280px;max-width:100%;margin-left:50px;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;background:#fff;">
                <div style="width:100%;aspect-ratio:1/1;background:#f3f4f6;overflow:hidden;">{img_html}</div>
                <div style="padding:10px 12px;">
                    <div style="font-size:14px;font-weight:600;color:#1f1f1f;line-height:1.45;">{title}</div>
                    <div style="margin-top:6px;font-size:12px;color:#ff2442;font-weight:600;">¥0</div>
                    <div style="margin-top:2px;font-size:12px;color:#6b7280;">{tag}</div>
                    <div style="margin-top:8px;display:flex;align-items:center;">{avatar_html}<span style="font-size:12px;color:#4b5563;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{user_name}</span></div>
                </div>
            </div>
        </div>
        '''

    def load_json_content():
        data = load_card_json()
        if not data:
            ui.notify('加载失败：无法读取 xhs3.json', color='negative')
            return
        fields['title'].value = data.get('defaultTitle', '')
        fields['image'].value = data.get('defaultImage', '')
        fields['user_name'].value = data.get('userInfo', {}).get('userName', '')
        fields['avatar'].value = data.get('userInfo', {}).get('avatar', '')
        fields['tag'].value = (data.get('tagStrategyMap', {}).get('after_price', [{}])[0].get('tag_content', {}).get('content', ''))
        fields['link'].value = data.get('userInfo', {}).get('userLink', '')
        refresh_preview()

    def save_to_disk():
        data = load_card_json()
        if not data:
            ui.notify('保存失败：无法读取 xhs3.json', color='negative')
            return
        data['defaultTitle'] = fields['title'].value
        data['searchContent'] = fields['title'].value
        data['defaultSubTitle'] = fields['title'].value
        data['searchPrefixContent'] = fields['title'].value
        data['goodsBaseInfo']['title'] = fields['title'].value
        data['defaultImage'] = fields['image'].value
        data['goodsBaseInfo']['image']['url'] = fields['image'].value
        data['userInfo']['userName'] = fields['user_name'].value
        data['userInfo']['avatar'] = fields['avatar'].value
        data['tagStrategyMap']['after_price'][0]['tag_content']['content'] = fields['tag'].value
        data['userInfo']['userLink'] = fields['link'].value
        data['goodsBaseInfo']['link'] = fields['link'].value
        data['defaultDeeplink'][0]['bizParam']['shortLink'] = fields['link'].value
        save_card_json(data)
        ui.notify('卡片模板已保存！', color='positive')

    load_json_content()
