import httpx
import os
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
                value_label = ui.label('--').classes('text-3xl font-bold')
                sub_label = ui.label('加载中...').classes('text-xs text-gray-400')
    return {'value': value_label, 'sub': sub_label}


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
            cards['server']['value'].classes(remove='text-red-500 text-green-500', add='text-green-500' if online else 'text-red-500')
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
            cards['key']['sub'].set_text(info.get('reason') or 'Key 无效')
            cards['key']['value'].classes(remove='text-green-500 text-red-500', add='text-red-500')
    except Exception as e:
        cards['key']['value'].set_text('未配置')
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

        async def refresh_all():
            await _refresh_stats(cards)
            await load_readme()

        ui.timer(30, refresh_all)
        ui.timer(0.1, refresh_all, once=True)


def main_page():
    if not app.storage.user.get('authenticated', False):
        return
    app.storage.user['view'] = 'home'
    with ui.header().classes('bg-gradient-to-r from-indigo-600 to-purple-600 items-center').props('elevated'):
        ui.button(icon='menu', on_click=lambda: drawer.toggle(), color='white').props('flat round')
        ui.label('小红书控制面板').classes('text-xl font-bold text-white')
        ui.space()
        with ui.row().classes('items-center gap-2'):
            ui.image('/img/header_logo.png').style('height: 40px; width: 40px;')
            ui.label('欢迎，' + str(app.storage.user.get('username', ''))).classes('text-white')
        ui.button(icon='logout', on_click=logout, color='white').props('flat round').tooltip('退出登录')
    with ui.left_drawer(value=False).classes('bg-gray-50 dark:bg-gray-900').props('bordered') as drawer:
        with ui.column().classes('w-full gap-1 p-2'):
            for view_name, item in MENU_ITEMS.items():
                btn = ui.button(item['name'], on_click=lambda v=view_name: change_view(v)).props('flat').classes('w-full justify-start')
                btn.props(f'icon={item["icon"]}')
    with ui.column().classes('w-full p-6'):
        content_container = ui.column().classes('w-full')

    def change_view(view_name: str):
        app.storage.user['view'] = view_name
        content_container.clear()
        if view_name == 'home':
            render_home()
        elif view_name == 'button1':
            create_runner_ui()
        elif view_name == 'button2':
            create_settings_ui()
        elif view_name == 'button4':
            create_card_editor_ui()
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

    change_view('home')


def logout():
    app.storage.user.clear()
    ui.navigate.to('/')


@ui.page('/')
def index_page():
    if app.storage.user.get('authenticated', False):
        main_page()
    else:
        with ui.column().classes('w-full h-screen items-center justify-center bg-cover'):
            with ui.card().classes('w-96 rounded-2xl shadow-xl p-8'):
                with ui.column().classes('w-full items-center gap-4'):
                    ui.image('/img/login_bg.webp').classes('w-40 h-40 rounded-full object-cover')
                    ui.label('小红书控制面板').classes('text-2xl font-bold')
                    username_input = ui.input('用户名', placeholder='请输入用户名').props('outlined').classes('w-full')
                    password_input = ui.input('密码', password=True, placeholder='请输入密码').props('outlined').classes('w-full')

                    async def do_login():
                        from auth import authenticate
                        if authenticate(username_input.value or '', password_input.value or ''):
                            app.storage.user.update({'authenticated': True, 'username': username_input.value})
                            ui.navigate.to('/')
                        else:
                            ui.notify('用户名或密码错误！', color='negative')

                    ui.button('登 录', on_click=do_login, icon='login', color='primary').classes('w-full')

app.add_static_files('/img', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'img'))
ui.run(storage_secret=os.getenv('NICEGUI_SECRET', 'change_me_in_production'), title='小红书控制面板', reload=False, dark=False)
