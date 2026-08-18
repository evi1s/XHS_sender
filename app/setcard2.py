import asyncio
import json
import html as html_mod
from nicegui import ui
from zw_obfuscate import ensure_zero_width

JSON_FILE_PATH = 'xhs2.json'


def _struct_signature(obj):
    
    if isinstance(obj, dict):
        return ('dict', [(k, _struct_signature(v)) for k, v in obj.items()])
    if isinstance(obj, list):
        return ('list', [_struct_signature(v) for v in obj])
    return (type(obj).__name__,)


def _preview_card_html(fields: dict) -> str:
    
    title = html_mod.escape(fields.get('title') or '卡片标题')
    time_text = html_mod.escape(fields.get('time') or '')
    location = html_mod.escape(fields.get('location') or '')
    image_url = html_mod.escape(fields.get('image') or '')

    img_html = (f'<img src="{image_url}" alt="卡片图" style="width:100%;height:100%;object-fit:cover;display:block;" '
                f'onerror="this.style.display=\'none\'">'
                if image_url else '')

    
    location_pin = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#6b7280" '
                    'style="width:12px;height:12px;flex-shrink:0;"><path d="M12 2C8.13 2 5 5.13 5 9c0 '
                    '5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5A2.5 2.5 0 1 1 12 6a2.5 2.5 0 0 1 '
                    '0 5.5z"/></svg>')
    
    calendar_icon = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
                     'stroke="#6b7280" stroke-width="2" style="width:12px;height:12px;flex-shrink:0;">'
                     '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/>'
                     '<line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>')

    return f'''
    <div style="position:relative;width:330px;max-width:100%;margin:0 auto;">
        <div style="width:280px;max-width:100%;margin-left:50px;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;background:#fff;
                    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.06);">
            <div style="width:100%;aspect-ratio:1/1;background:#f3f4f6;overflow:hidden;">{img_html}</div>
            <div style="padding:10px 12px;">
                <div style="font-size:14px;font-weight:600;color:#1f1f1f;line-height:1.45;
                            display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">{title}</div>
                <div style="margin-top:5px;display:flex;align-items:center;gap:4px;font-size:12px;color:#6b7280;line-height:1.4;">
                    {calendar_icon}<span>{time_text}</span>
                </div>
                <div style="margin-top:3px;display:flex;align-items:center;gap:4px;font-size:12px;color:#6b7280;line-height:1.4;">
                    {location_pin}<span>{location}</span>
                </div>
            </div>
        </div>
    </div>'''


def create_card_editor_ui2(switch_view=None):
    

    fields = {}
    preview_html = None

    def load_from_disk():
        try:
            with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            ui.notify(f'文件 {JSON_FILE_PATH} 不存在，保存后将自动创建。', color='info')
            return {}
        except Exception as e:
            ui.notify(f'读取文件时出错: {e}', color='negative')
            return {}

    def refresh_preview():
        if preview_html is not None:
            preview_html.set_content(_preview_card_html({k: v.value for k, v in fields.items()}))

    async def load_json_content():
        data = await asyncio.to_thread(load_from_disk)
        fields['title'].value = data.get('title', data.get('defaultTitle', ''))
        fields['time'].value = data.get('time', '')
        fields['location'].value = data.get('location', '')
        fields['image'].value = data.get('image', data.get('defaultImage', ''))
        fields['link'].value = data.get('deeplink', '')
        refresh_preview()

    def save_to_disk():
        try:
            with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
                original_text = f.read()
                f.seek(0)
                data = json.load(f)
        except FileNotFoundError:
            data = {}
            original_text = None
        except Exception as e:
            ui.notify(f'读取文件时出错: {e}', color='negative')
            return

        original_sig = _struct_signature(data)

        
        title = ensure_zero_width(fields['title'].value or '')
        time_text = ensure_zero_width(fields['time'].value or '')
        location = ensure_zero_width(fields['location'].value or '')
        image_url = fields['image'].value or ''
        link = fields['link'].value or ''

        
        for k in ('title', 'defaultTitle', 'defaultSubTitle'):
            if k in data:
                data[k] = title
        if 'time' in data:
            data['time'] = time_text
        if 'location' in data:
            data['location'] = location
        for k in ('image', 'defaultImage', 'coverImage'):
            if k in data:
                data[k] = image_url
        for k in ('deeplink', 'defaultDeeplink', 'clickReferenceMessageDeeplink'):
            if k in data:
                data[k] = link

        
        new_sig = _struct_signature(data)
        if new_sig != original_sig:
            ui.notify('保存中止：字段结构发生变化（与原模板不一致），未写入文件。', color='negative')
            return

        try:
            with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            ui.notify('卡片已保存！', color='positive')
        except Exception as e:
            if original_text is not None:
                try:
                    with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
                        f.write(original_text)
                except Exception:
                    pass
            ui.notify(f'保存失败: {e}（已尝试恢复原文件）', color='negative')

    def _add_field(label, key, placeholder=''):
        fields[key] = ui.input(label, placeholder=placeholder).classes('w-full')

    with ui.card().classes('w-full max-w-5xl mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-indigo-600 to-purple-600 rounded-t-2xl px-4 py-3'):
            ui.icon('style', size='28px').classes('text-white')
            ui.label('卡片消息2（博主/活动卡片）').classes('text-xl font-bold text-white')
            ui.space()
        with ui.row().classes('w-full items-center gap-2 px-4 pt-3'):
            ui.button('卡片消息', icon='style', on_click=(lambda: switch_view('button4')) if switch_view else None).props('color=primary')
            ui.button('卡片消息2', icon='style', on_click=(lambda: switch_view('button10')) if switch_view else None).props('disabled')
        with ui.column().classes('w-full gap-4 px-4 py-4'):
            with ui.row().classes('w-full items-start gap-6'):
                with ui.column().classes('w-1/2 gap-2'):
                    with ui.card().classes('w-full p-4'):
                        ui.label('➊ 标题与内容').classes('font-bold text-primary mb-2')
                        _add_field('主标题（同步 3 处字段）', 'title', '例如：点击找到我 | 如梦')
                        _add_field('卡片图片 URL（同步 3 处字段）', 'image', 'https://...')

                    with ui.card().classes('w-full p-4'):
                        ui.label('➋ 显示信息位置').classes('font-bold text-primary mb-2')
                        _add_field('副标题（time 字段）', 'time', '例如：旅行博主/旅行创业')
                        _add_field('标签（location 字段）', 'location', '例如：官方认证')

                    with ui.card().classes('w-full p-4'):
                        ui.label('➌ 跳转链接(先“短链生成”后的外部地址或企业微信Url)').classes('font-bold text-primary mb-2')
                        _add_field('跳转 URL（同步 3 处字段）', 'link', 'https://...')

                    with ui.row().classes('w-full gap-4 mt-2'):
                        ui.button('保存到文件', icon='save', on_click=save_to_disk, color='primary')
                        ui.button('重新加载', icon='refresh', on_click=load_json_content)

                with ui.column().classes('w-80 justify-center items-center gap-2'):
                    ui.label('👁️ 实时预览').classes('font-bold text-gray-500')
                    with ui.column().classes('relative').style('width:330px;max-width:100%;'):
                        preview_html = ui.html('').classes('w-full')
                        ui.image('/img/card_icon1.jpg').style(
                            'position:absolute;top:-12px;left:-6px;width:42px;height:42px;border-radius:50%;'
                            'z-index:10;border:2px solid #fff;box-shadow:0 2px 8px rgba(255,36,66,.45);'
                            'object-fit:cover;'
                        )

            for f in fields.values():
                f.on_value_change(refresh_preview)

    ui.timer(0.2, load_json_content, once=True)
