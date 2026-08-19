import httpx
import time
import psutil
import config
from datetime import datetime
from nicegui import app, ui
from database import connect_to_mongo, close_mongo_connection
from runapp import create_runner_ui
from config import ADMIN_USERNAME, ADMIN_PASSWORD, PROXY_SERVER_URL, MONGO_USER_ID_COLLECTION, PROXY_API_KEY
from settings import create_settings_ui
from setcard import create_card_editor_ui
from setcard2 import create_card_editor_ui2
from devices.ui import create_device_management_ui
from devices.list_ui import create_device_list_ui
from devices.data import get_devices_collection, get_collection
from adduserid import create_ui as create_userid_ui
from addtext import create_ui as create_text_ui
from xhs_shorturl import create_ui as create_shorturl_ui
from authorize import create_ui as create_authorize_ui
import runapp

README_URL = "https://commteam.it.com/web/readme.txt"
LOGIN_BG_URL = "/img/login_bg.webp"
CONTACT_US_URL = ""

MENU_ITEMS = {
    'home': {'name': '主页', 'icon': 'home'},
    'button1': {'name': '执行程序', 'icon': 'play_circle_outline'},
    'button2': {'name': '软件设置', 'icon': 'build_circle'},
    'button5': {'name': '设备管理', 'icon': 'devices_other'},
    'button9': {'name': '设备列表', 'icon': 'view_list'},
    'button6': {'name': '客户管理', 'icon': 'group_add'},
    'button7': {'name': '文字消息', 'icon': 'rate_review'},
    'button4': {'name': '卡片消息', 'icon': 'style'},
    'button10': {'name': '卡片消息2', 'icon': 'style'},
    'button8': {'name': '短链生成', 'icon': 'link'},
    'authorize': {'name': '授权设置', 'icon': 'vpn_key'},
}


def _stat_card(title: str, icon: str, color: str) -> dict:
                                          
    with ui.card().classes('w-60 rounded-2xl shadow-lg bg-white dark:bg-gray-800'):
        with ui.row().classes('items-center gap-4'):
            with ui.element('div').classes(f'w-12 h-12 rounded-xl bg-gradient-to-br {color} flex items-center justify-center shrink-0'):
                ui.icon(icon).classes('text-white text-2xl')
            with ui.column().classes('gap-0'):
                ui.label(title).classes('text-sm text-gray-500 dark:text-gray-400')
                with ui.row().classes('items-baseline gap-1.5'):
                    value_label = ui.label('--').classes('text-3xl font-bold')
                    extra_label = ui.label('').classes('text-xs text-gray-400 break-all')
                sub_label = ui.label('加载中...').classes('text-xs text-gray-400 break-all')
    return {'value': value_label, 'sub': sub_label, 'extra': extra_label}


async def _refresh_stats(cards: dict):
                                              
    try:
        proc = getattr(runapp, 'SCRIPT_PROCESS', None)
        running = proc is not None and getattr(proc, 'returncode', None) is None
        if running:
            cards['runner']['value'].set_text('运行中')
            cards['runner']['sub'].set_text(f'PID {proc.pid} · main_sse.py')
            cards['runner']['value'].classes(remove='text-red-500 text-green-500', add='text-green-500')
        else:
            cards['runner']['value'].set_text('已停止')
            cards['runner']['sub'].set_text('暂无发私信任务')
            cards['runner']['value'].classes(remove='text-green-500 text-red-500', add='text-red-500')
    except Exception as e:
        cards['runner']['value'].set_text('未知')
        cards['runner']['sub'].set_text(f'{type(e).__name__}')

    try:
        cards['devices']['value'].set_text(str(get_devices_collection().count_documents({})))
        cards['devices']['sub'].set_text('发送设备')
    except Exception as e:
        cards['devices']['value'].set_text('N/A')
        cards['devices']['sub'].set_text(f'错误: {type(e).__name__}')

    try:
        today = datetime.now().strftime('%Y-%m-%d')
        docs = get_devices_collection().find({'last_usage_date': today}, {'daily_usage_count': 1})
        used = sum(d.get('daily_usage_count', 0) for d in docs)
        cards['usage']['value'].set_text(str(used))
        cards['usage']['sub'].set_text(f'今日 {today}')
    except Exception:
        cards['usage']['value'].set_text('N/A')
        cards['usage']['sub'].set_text('查询失败')

    try:
        n_userids = get_collection(MONGO_USER_ID_COLLECTION).count_documents({})
        cards['userids']['value'].set_text(str(n_userids))
        cards['userids']['sub'].set_text('待发送的接收方')
    except Exception:
        cards['userids']['value'].set_text('N/A')
        cards['userids']['sub'].set_text('查询失败')

    try:
        vm = psutil.virtual_memory()
        cards['memory']['value'].set_text(f'{vm.percent}%')
        cards['memory']['sub'].set_text(f'已用 {vm.used / 1024**3:.1f} / {vm.total / 1024**3:.1f} GB')
    except Exception:
        cards['memory']['value'].set_text('N/A')
        cards['memory']['sub'].set_text('不可用')

    try:
        async with httpx.AsyncClient(timeout=5) as c:
            t0 = time.time()
            r = await c.get('https://www.baidu.com', follow_redirects=True)
            ok = r.status_code < 400
            ms = int((time.time() - t0) * 1000)
        cards['network']['value'].set_text('正常' if ok else '异常')
        cards['network']['sub'].set_text(f'{ms} ms')
        cards['network']['value'].classes(remove='text-red-500 text-green-500', add='text-green-500' if ok else 'text-red-500')
    except Exception:
        cards['network']['value'].set_text('离线')
        cards['network']['sub'].set_text('无法访问外网')
        cards['network']['value'].classes(remove='text-red-500 text-green-500', add='text-red-500')

    try:
        api_key = (getattr(config, 'PROXY_API_KEY', '') or '').strip()
        headers = {'X-API-Key': api_key} if api_key else {}
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.post(PROXY_SERVER_URL, json={}, headers=headers)
        status = r.status_code
        online = status in (200, 400, 401, 422)
        if status == 401:
            cards['server']['value'].set_text('在线')
            cards['server']['sub'].set_text(f'状态码:{status} Key无效')
            cards['server']['value'].classes(remove='text-green-500 text-red-500', add='text-red-500')
        else:
            cards['server']['value'].set_text('在线' if online else f'HTTP {status}')
            cards['server']['sub'].set_text(f'状态码:{status} Key有效')
            cards['server']['value'].classes(remove='text-green-500 text-red-500', add='text-green-500' if online else 'text-red-500')
    except Exception as e:
        cards['server']['value'].set_text('离线')
        cards['server']['sub'].set_text(f'{type(e).__name__}')
        cards['server']['value'].classes(remove='text-green-500 text-red-500', add='text-red-500')

    try:
        api_key = (getattr(config, 'PROXY_API_KEY', '') or '').strip()
        base = PROXY_SERVER_URL.split('/execute-task')[0]
        async with httpx.AsyncClient(timeout=6) as c:
            r = await c.get(base + '/customer/status', headers={'X-API-Key': api_key})
            info = r.json()
        if info.get('valid'):
            _cid = info.get('customer_id') or ''
            cards['key']['extra'].set_text(f'ID:{_cid}' if _cid else '')
            remaining = info.get('remaining')
            days = info.get('remaining_days')
            expire = (info.get('expire_at') or '')[:10]
            if remaining is not None:
                cards['key']['value'].set_text(str(remaining))
                cards['key']['sub'].set_text(f'剩余 {remaining}/{info.get("quota")} 次 · {info.get("plan_type")}')
            elif days is not None:
                cards['key']['value'].set_text(f'{days:.0f}天')
                cards['key']['sub'].set_text(f'到期 {expire} · {info.get("plan_type")}')
            else:
                cards['key']['value'].set_text('∞')
                cards['key']['sub'].set_text('不限次数 · 不限时间')
            cards['key']['value'].classes(remove='text-red-500 text-green-500', add='text-green-500')
        else:
            cards['key']['value'].set_text('失效')
            cards['key']['extra'].set_text('')
            cards['key']['sub'].set_text(info.get('reason') or 'Key 无效')
            cards['key']['value'].classes(remove='text-green-500 text-red-500', add='text-red-500')
    except Exception as e:
        cards['key']['value'].set_text('未配置')
        cards['key']['extra'].set_text('')
        cards['key']['sub'].set_text(f'{type(e).__name__}')
        cards['key']['value'].classes(remove='text-green-500 text-red-500', add='text-red-500')


def render_home():
                             
    with ui.column().classes('w-full max-w-5xl gap-6'):
        with ui.card().classes('w-full rounded-2xl'):
            readme_display = ui.html('<div style="text-align:right;width:100%"><div style="display:inline-block;text-align:left;background-color:#fdf7e9;border-left:5px solid #f0ad4e;padding:12px 15px;border-radius:5px"><h3 style="margin:0;color:#c08b3a">正在加载公告...</h3></div></div>')

        with ui.card().classes('w-full rounded-2xl bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-pink-500/10'):
            with ui.row().classes('items-center justify-between w-full'):
                with ui.column().classes('gap-1'):
                    ui.label('系统概览').classes('text-xl font-bold')
                    ui.label('设备、用量、网络与服务端状态（每 30 秒自动刷新）').classes('text-sm text-gray-500 dark:text-gray-400')
                ui.icon('dashboard_customize', size='48px').classes('text-indigo-400')

        with ui.row().classes('w-full gap-4 flex-wrap'):
            cards = {
                'runner': _stat_card('执行程序', 'play_circle', 'from-slate-500 to-gray-600'),
                'devices': _stat_card('帐号数量', 'devices_other', 'from-blue-500 to-indigo-500'),
                'usage': _stat_card('今日送达', 'trending_up', 'from-green-500 to-emerald-500'),
                'userids': _stat_card('客户余量', 'group', 'from-amber-500 to-orange-500'),
                'memory': _stat_card('系统内存', 'memory', 'from-purple-500 to-fuchsia-500'),
                'network': _stat_card('网络状态', 'wifi', 'from-cyan-500 to-sky-500'),
                'server': _stat_card('服务状态', 'cloud', 'from-rose-500 to-pink-500'),
                'key': _stat_card('Key时效', 'vpn_key', 'from-teal-500 to-cyan-500'),
            }


        async def load_readme():
            try:
                async with httpx.AsyncClient(timeout=10.0) as c:
                    r = await c.get(README_URL)
                    r.raise_for_status()
                    readme_display.set_content(f'<div style="text-align:right;width:100%"><div style="display:inline-block;text-align:left">{r.text}</div></div>')
            except Exception as e:
                readme_display.set_content(f"<div style='text-align:right;width:100%'><div style='display:inline-block;text-align:left;background-color:#fdf7e9;border-left:5px solid #f0ad4e;padding:12px 15px;border-radius:5px'><h3 style='margin:0'>加载公告失败</h3><p style='margin:4px 0 0'><code>{type(e).__name__}: {e}</code></p></div></div>")

        ui.timer(0.3, lambda: _refresh_stats(cards), once=True)
        ui.timer(30, lambda: _refresh_stats(cards))
        ui.timer(0.5, load_readme, once=True)


@ui.page('/')
async def main_page():
    ui.add_head_html('<script src="https://plugin-code.salesmartly.com/js/project_8724_730398_1778521721.js"></script>')

    dark = ui.dark_mode()

    if not app.storage.user.get('authenticated'):
        ui.query('body').style(f'''
            background-image: url("{LOGIN_BG_URL}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        ''')

        with ui.column().classes('absolute-center items-center gap-4'):
            with ui.card().classes('w-96 p-8 rounded-lg shadow-xl bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm'):
                ui.label('小红书控制面板(3.3)').classes('self-center text-2xl font-semibold text-gray-800 dark:text-white')
                username = ui.input('账号').props('outlined dense').classes('w-full')
                password = ui.input('密码', password=True, password_toggle_button=True).props('outlined dense').classes('w-full')

                async def attempt_login():
                    is_valid = (username.value == ADMIN_USERNAME and password.value == ADMIN_PASSWORD)
                    if is_valid:
                        app.storage.user.update({'authenticated': True, 'username': username.value, 'view': 'home'})
                        ui.navigate.to('/')
                    else:
                        ui.notify('账号或密码错误', color='negative', icon='warning')

                ui.button('登录', on_click=attempt_login).classes('w-full mt-4 py-3')
                ui.button('联系客服↘', on_click=lambda: ui.navigate.to(CONTACT_US_URL, new_tab=True), icon='support_agent') \
                    .props('flat text-color="grey-8"') \
                    .classes('w-full mt-2')

        return

    app.storage.user['view'] = 'home'

    with ui.header(elevated=True).classes('justify-between items-center px-8 py-2 text-white bg-gradient-to-r from-indigo-600 to-purple-600'):
        with ui.row().classes('items-center gap-4'):
            ui.image('/img/header_logo.png').style('height: 40px; width: 40px;')
            ui.label('小红书私信控制面板(Beta_3.3)').classes('text-2xl font-bold')
        with ui.row().classes('items-center gap-4'):
            ui.label(f'欢迎, {app.storage.user.get("username")}!').classes('text-lg')
            def logout():
                app.storage.user.clear()
                ui.navigate.to('/')
            ui.button(icon='logout', on_click=logout).props('flat round text-color="white"').tooltip('退出登录')

    menu_items_ui = {}
    content_container = ui.column().classes('w-full p-4 md:p-8')

    def change_view(view_name: str):
        app.storage.user['view'] = view_name

        active_class = 'bg-gray-200 dark:bg-gray-700'
        for name, item in menu_items_ui.items():
            if name == view_name:
                item.classes(add=active_class)
            else:
                item.classes(remove=active_class)

        centered_views = ['home', 'button1', 'button2', 'button3', 'button4', 'button5', 'button6', 'button7', 'button8', 'button9', 'button10', 'authorize']

        if view_name in centered_views:
            content_container.classes(add='items-center')
        else:
            content_container.classes(remove='items-center')

        content_container.clear()
        with content_container:
            ui.label(MENU_ITEMS[view_name]['name']).classes('text-3xl font-bold mb-4')
            ui.separator().classes('mb-8')
            if view_name == 'home':
                render_home()
            elif view_name == 'button1':
                create_runner_ui()
            elif view_name == 'button2':
                create_settings_ui()
            elif view_name == 'button4':
                create_card_editor_ui(switch_view=change_view)
            elif view_name == 'button10':
                create_card_editor_ui2(switch_view=change_view)
            elif view_name == 'button5':
                create_device_management_ui()
            elif view_name == 'button6':
                create_userid_ui()
            elif view_name == 'button7':
                create_text_ui()
            elif view_name == 'button8':
                create_shorturl_ui()
            elif view_name == 'button9':
                create_device_list_ui()
            elif view_name == 'authorize':
                create_authorize_ui()
            else:
                readme_display = ui.html("<h3>正在加载主页内容...</h3>")

                async def load_readme():
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as c:
                            r = await c.get(README_URL)
                            r.raise_for_status()
                            readme_display.set_content(r.text)
                    except Exception as e:
                        readme_display.set_content(
                            f"<h3>加载主页内容失败</h3>"
                            f"<p><strong>URL:</strong> <code>{README_URL}</code></p>"
                            f"<p><strong>错误:</strong> <code>{type(e).__name__}</code></p>"
                        )

                ui.timer(0.5, load_readme, once=True)

    with ui.left_drawer().classes('bg-gray-100 dark:bg-gray-800 p-4'):
        with ui.row().classes('items-center gap-2 px-4 pb-4'):
            ui.icon('menu', size='md')
            ui.label('导航菜单').classes('text-lg font-semibold')

        for name, details in MENU_ITEMS.items():
            if name == 'button10':
                continue
            with ui.item(on_click=lambda n=name: change_view(n)) \
                    .classes('w-full rounded-lg cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700') as item:
                menu_items_ui[name] = item
                with ui.item_section().props('avatar'):
                    ui.icon(details['icon'])
                with ui.item_section():
                    ui.label(details['name'])

    with ui.page_sticky(position='bottom-right', x_offset=90, y_offset=40):
        with ui.row().classes('gap-4'):
            ui.button(on_click=lambda: dark.set_value(not dark.value), color='primary') \
                .props('fab') \
                .bind_icon_from(dark, 'value', lambda v: 'light_mode' if v else 'dark_mode') \
                .tooltip('切换亮色/暗色主题')

    change_view('home')


app.add_static_files('/img', '/root/nicegui/img')
app.on_startup(connect_to_mongo)
app.on_shutdown(close_mongo_connection)

ui.run(storage_secret='a_very_long_and_super_secret_string_123!@#',
       title='小红书控制面板(Beta_3.3)',
       reload=False,
       dark=False)
