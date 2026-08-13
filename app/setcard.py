import asyncio
import json
import html as html_mod
from nicegui import ui

JSON_FILE_PATH = 'xhs3.json'


def _struct_signature(obj):
    """递归计算 JSON 结构签名（key 顺序 + 类型 + 嵌套结构），用于校验格式不变。"""
    if isinstance(obj, dict):
        return ('dict', [(k, _struct_signature(v)) for k, v in obj.items()])
    if isinstance(obj, list):
        return ('list', [_struct_signature(v) for v in obj])
    return (type(obj).__name__,)


def _preview_card_html(fields: dict) -> str:
    """根据字段生成卡片预览 HTML（图片→标题→价格行→底行：头像+昵称）。"""
    title = html_mod.escape(fields.get('title') or '卡片标题')
    user_name = html_mod.escape(fields.get('user_name') or '卖家昵称')
    tag_text = html_mod.escape(fields.get('tag_text') or '')
    price = fields.get('price')
    price_str = f'¥{price}' if price is not None else '¥0'
    image_url = html_mod.escape(fields.get('image') or '')
    avatar = html_mod.escape(fields.get('avatar') or '')

    img_html = (f'<img src="{image_url}" alt="卡片图" style="width:100%;height:100%;object-fit:cover;display:block;" '
                f'onerror="this.style.display=\'none\'">'
                if image_url else '')

    avatar_html = (f'<img src="{avatar}" alt="头像" style="width:18px;height:18px;border-radius:50%;'
                   f'object-fit:cover;background:#f3f4f6;flex-shrink:0;" '
                   f'onerror="this.style.display=\'none\'">' if avatar else '')

    return f'''
    <div style="width:280px;max-width:100%;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;background:#fff;
                font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.06);">
        <div style="width:100%;aspect-ratio:1/1;background:#f3f4f6;overflow:hidden;">{img_html}</div>
        <div style="padding:10px 12px;">
            <div style="font-size:14px;font-weight:600;color:#1f1f1f;line-height:1.45;
                        display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">{title}</div>
            <div style="margin-top:6px;font-size:12px;line-height:1.4;">
                <span style="font-weight:600;color:#ff2442;">{price_str}</span>
                <span style="color:#6b7280;margin-left:6px;">{tag_text}</span>
            </div>
            <div style="margin-top:8px;display:flex;align-items:center;gap:6px;min-width:0;">
                {avatar_html}
                <span style="font-size:12px;color:#4b5563;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{user_name}</span>
            </div>
        </div>
    </div>'''


def create_card_editor_ui():
    """模块化卡片编辑器：左侧表单 + 右侧实时预览，保存时同步所有关联字段且保证 JSON 格式不变。"""
    ui.label('卡片消息设置').classes('text-2xl font-bold mb-1')
    ui.label(f'配置文件: {JSON_FILE_PATH} · 修改字段后点击「保存到文件」生效').classes('text-sm text-gray-500 mb-4')

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
        gb = (data.get('goodsBaseInfo') or {})
        img = (gb.get('image') or {})
        after_price = ((data.get('tagStrategyMap') or {}).get('after_price') or [{}])
        tag_content = (after_price[0].get('tag_content') or {}) if after_price else {}
        fields['title'].value = data.get('defaultTitle', '')
        fields['image'].value = data.get('defaultImage', '') or img.get('url', '')
        fields['user_name'].value = (data.get('userInfo') or {}).get('userName', '')
        fields['avatar'].value = (data.get('userInfo') or {}).get('avatar', '')
        fields['price'].value = data.get('expectedPrice', 0)
        fields['tag_text'].value = tag_content.get('content', '')
        fields['link'].value = (data.get('userInfo') or {}).get('userLink', '')
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

        title = fields['title'].value or ''
        image_url = fields['image'].value or ''
        user_name = fields['user_name'].value or ''
        avatar = fields['avatar'].value or ''
        price = int(fields['price'].value or 0)
        tag_text = fields['tag_text'].value or ''
        link = fields['link'].value or ''

        if 'defaultTitle' in data:
            data['defaultTitle'] = title
        if 'searchContent' in data:
            data['searchContent'] = title
        if 'defaultSubTitle' in data:
            data['defaultSubTitle'] = title
        if 'searchPrefixContent' in data:
            data['searchPrefixContent'] = title
        gb = data.get('goodsBaseInfo')
        if isinstance(gb, dict):
            if 'title' in gb:
                gb['title'] = title
            if 'link' in gb:
                gb['link'] = link
            img = gb.get('image')
            if isinstance(img, dict) and 'url' in img:
                img['url'] = image_url
        if 'defaultImage' in data:
            data['defaultImage'] = image_url
        ui_info = data.get('userInfo')
        if isinstance(ui_info, dict):
            if 'userName' in ui_info:
                ui_info['userName'] = user_name
            if 'avatar' in ui_info:
                ui_info['avatar'] = avatar
            if 'userLink' in ui_info:
                ui_info['userLink'] = link
        if 'expectedPrice' in data:
            data['expectedPrice'] = price
        ts_map = data.get('tagStrategyMap')
        if isinstance(ts_map, dict):
            after_price = ts_map.get('after_price')
            if isinstance(after_price, list) and after_price:
                tc = after_price[0].get('tag_content')
                if isinstance(tc, dict) and 'content' in tc:
                    tc['content'] = tag_text
        dd = data.get('defaultDeeplink')
        if isinstance(dd, list) and dd:
            bp = dd[0].get('bizParam')
            if isinstance(bp, dict) and 'shortLink' in bp:
                bp['shortLink'] = link

        new_sig = _struct_signature(data)
        if new_sig != original_sig:
            ui.notify('保存中止：字段结构发生变化（与原模板不一致），未写入文件。', color='negative')
            return

        try:
            with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent='\t')
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
        fields[key] = ui.input(label, placeholder=placeholder).classes('w-1/2')

    with ui.row().classes('w-full items-start gap-6'):
        with ui.column().classes('w-1/2 gap-2'):
            with ui.card().classes('w-full p-4'):
                ui.label('➊ 标题与内容').classes('font-bold text-primary mb-2')
                _add_field('卡片标题（同步 5 处字段）', 'title', '例如：快速精准引流，高效客户转化')
                _add_field('卡片图片 URL（图片上文字需换图）', 'image', 'https://...')

            with ui.card().classes('w-full p-4'):
                ui.label('➋ 显示信息位置').classes('font-bold text-primary mb-2')
                _add_field('卖家昵称（底部用户名）', 'user_name', '例如：薯队长推荐🔥')
                _add_field('头像 URL（底行显示圆形头像）', 'avatar', 'https://...')

            with ui.card().classes('w-full p-4'):
                ui.label('❸ 显示信息位置').classes('font-bold text-primary mb-2')
                with ui.row().classes('w-full gap-4'):
                    fields['price'] = ui.number('价格', value=0).classes('w-20')
                    fields['tag_text'] = ui.input('标签文案（如：点击加微信详聊）', value='').classes('flex-1')

            with ui.card().classes('w-full p-4'):
                ui.label('➍ 跳转链接(先“短链生成”后的外部地址或企业微信Url)').classes('font-bold text-primary mb-2')
                _add_field('短链 URL（同步 3 处字段）', 'link', 'https://...')

            with ui.row().classes('w-full gap-4 mt-2'):
                ui.button('保存到文件', icon='save', on_click=save_to_disk, color='primary')
                ui.button('重新加载', icon='refresh', on_click=load_json_content)

        with ui.column().classes('w-80'):
            ui.label('👁️ 实时预览').classes('font-bold text-gray-500 mb-2')
            preview_html = ui.html('').classes('w-full')

    for f in fields.values():
        f.on_value_change(refresh_preview)

    ui.timer(0.2, load_json_content, once=True)
