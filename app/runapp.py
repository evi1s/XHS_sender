import asyncio
import os
import signal
import sys
from nicegui import ui

SCRIPT_PROCESS = None
SCRIPT_LOG = ''


def create_runner_ui():
    global SCRIPT_PROCESS, SCRIPT_LOG
    with ui.card().classes('w-full max-w-[98%] mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-emerald-600 to-teal-600 rounded-t-2xl px-4 py-3'):
            ui.icon('play_circle_outline', size='28px').classes('text-white')
            ui.label('执行程序').classes('text-xl font-bold text-white')
            ui.space()
            ui.button('开始', on_click=start_script, icon='play_arrow', color='white').props('flat text-color=primary')
            ui.button('停止', on_click=stop_script, icon='stop', color='white').props('flat text-color=negative')
            ui.button('清屏', on_click=clear_log, icon='cleaning_services', color='white').props('flat text-color=primary')
        with ui.column().classes('w-full gap-2 px-4 py-4'):
            terminal = ui.terminal(auto_scroll=True).classes('w-full')
            terminal.props('rows=50 cols=260 scrollback=10000')

    def log_line(msg: str):
        global SCRIPT_LOG
        SCRIPT_LOG = (SCRIPT_LOG + msg + '\n')[-20000:]
        terminal.push(msg)

    async def start_script():
        global SCRIPT_PROCESS, SCRIPT_LOG
        if SCRIPT_PROCESS is not None and SCRIPT_PROCESS.returncode is None:
            ui.notify('任务已在运行中！', color='warning')
            return
        ui.notify('正在启动...', color='info')
        cmd = [sys.executable, 'main_sse.py']
        SCRIPT_PROCESS = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        log_line('--> [客户端-自动调度模式] 启动...')

        async def read_output():
            assert SCRIPT_PROCESS.stdout is not None
            while True:
                line = await SCRIPT_PROCESS.stdout.readline()
                if not line:
                    break
                log_line(line.decode('utf-8', errors='replace').rstrip())

        asyncio.create_task(read_output())
        asyncio.create_task(wait_process())

    async def wait_process():
        global SCRIPT_PROCESS
        if SCRIPT_PROCESS is None:
            return
        rc = await SCRIPT_PROCESS.wait()
        log_line(f'--> 任务进程已退出，退出码: {rc}')
        SCRIPT_PROCESS = None

    async def stop_script():
        global SCRIPT_PROCESS
        if SCRIPT_PROCESS is None or SCRIPT_PROCESS.returncode is not None:
            ui.notify('当前没有运行中的任务！', color='warning')
            return
        log_line('--> 正在停止任务...')
        SCRIPT_PROCESS.terminate()
        try:
            await asyncio.wait_for(SCRIPT_PROCESS.wait(), timeout=5)
        except asyncio.TimeoutError:
            SCRIPT_PROCESS.kill()
        log_line('--> 任务已停止。')

    def clear_log():
        global SCRIPT_LOG
        SCRIPT_LOG = ''
        terminal.clear()
