

import asyncio
import sys
import re
import os
import signal
from typing import List, Optional
import psutil
from nicegui import app, ui

SCRIPT_NAME = 'main_sse.py'
SCRIPT_PROCESS: Optional[asyncio.subprocess.Process] = None
RED = '\x1b[31m'
RESET = '\x1b[0m'
GLOBAL_LOG_CONTENT: List[str] = [
    "欢迎使用小红书自动消息发送程序！点击下方的“执行”按钮开始任务。",
    f"{RED}waning：运行之前请检查配置设置是否都已完成。运行过程中尽量不要修改配置{RESET}"
]


def clean_ansi(text: str) -> str:
    """移除ANSI转义字符"""
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*m')
    return ansi_pattern.sub('', text)


def kill_lingering_processes():
    current_pid = os.getpid()
    print("启动检查：正在查找残留的子进程...")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.pid == current_pid: continue
            cmdline = proc.cmdline()
            if cmdline and SCRIPT_NAME in cmdline:
                print(f"  找到残留进程 {proc.pid}，正在终止...")
                proc.kill()
                proc.wait()
                print(f"  进程 {proc.pid} 已终止。")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    print("检查完成")


@app.on_shutdown
async def cleanup_on_shutdown():
    print("应用即将关闭，正在清理进程...")
    if SCRIPT_PROCESS and SCRIPT_PROCESS.returncode is None:
        try:
            pid = SCRIPT_PROCESS.pid
            if sys.platform != "win32":
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            else:
                SCRIPT_PROCESS.kill()
            await SCRIPT_PROCESS.wait()
            print(f"子进程 {pid} 已被清理。")
        except Exception as e:
            print(f"清理子进程时出错: {e}")


async def run_script():
    """启动子进程并监控其输出"""
    global SCRIPT_PROCESS, GLOBAL_LOG_CONTENT
    if SCRIPT_PROCESS is not None and SCRIPT_PROCESS.returncode is None:
        ui.notify('任务已在运行中...', color='warning')
        return

    GLOBAL_LOG_CONTENT = ['开始执行程序....']

    try:
        preexec_fn = os.setsid if sys.platform != "win32" else None
        SCRIPT_PROCESS = await asyncio.create_subprocess_exec(
            sys.executable, SCRIPT_NAME,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            preexec_fn=preexec_fn
        )
        while SCRIPT_PROCESS.stdout:
            try:
                line_bytes = await asyncio.wait_for(SCRIPT_PROCESS.stdout.readline(), timeout=1.0)
                if not line_bytes: break
                cleaned_line = clean_ansi(line_bytes.decode(errors='ignore').strip())
                if cleaned_line:
                    GLOBAL_LOG_CONTENT.append(cleaned_line)
            except asyncio.TimeoutError:
                if SCRIPT_PROCESS.returncode is not None:
                    break
                continue

        await SCRIPT_PROCESS.wait()
        if '手动终止' not in '\n'.join(GLOBAL_LOG_CONTENT):
            GLOBAL_LOG_CONTENT.append(f'执行完毕，返回码: {SCRIPT_PROCESS.returncode}')

    except Exception as e:
        GLOBAL_LOG_CONTENT.append(f'执行过程中发生错误: {e}')
    finally:
        SCRIPT_PROCESS = None


async def kill_running_script():
    global SCRIPT_PROCESS, GLOBAL_LOG_CONTENT
    if not SCRIPT_PROCESS or SCRIPT_PROCESS.returncode is not None:
        ui.notify('当前没有运行的任务。', color='secondary')
        return

    GLOBAL_LOG_CONTENT.append('>>> 任务被手动终止...')
    ui.notify('正在发送终止信号...', color='orange')

    try:
        if sys.platform != "win32":
            os.killpg(os.getpgid(SCRIPT_PROCESS.pid), signal.SIGTERM)
        else:
            SCRIPT_PROCESS.terminate()

        await asyncio.wait_for(SCRIPT_PROCESS.wait(), timeout=5.0)
    except asyncio.TimeoutError:
        ui.notify('终止超时，强制结束任务...', color='negative')
        SCRIPT_PROCESS.kill()
        await SCRIPT_PROCESS.wait()
    except Exception as e:
        ui.notify(f'结束任务失败: {e}', color='negative')


def create_runner_ui():
    with ui.card().classes('w-full max-w-[98%] mx-auto rounded-2xl shadow-lg'):
        with ui.row().classes('w-full items-center bg-gradient-to-r from-emerald-600 to-teal-600 rounded-t-2xl px-4 py-3'):
            ui.icon('terminal', size='28px').classes('text-white')
            ui.label('任务执行').classes('text-xl font-bold text-white')
            ui.space()
            ui.label('日志实时输出').classes('text-white/80 text-sm mr-4')

        with ui.column().classes('w-full gap-4 px-4 py-4'):
            last_line_sent = 0

            terminal_options = {'rows': 50, 'cols': 400, 'wordWrap': False, 'scrollback': 10000}
            terminal = ui.xterm(terminal_options).classes('w-full rounded-xl border border-gray-300 dark:border-gray-700')
            terminal.props('style=min-height:65vh;height:65vh')

            with ui.row().classes('w-full justify-center gap-4 mt-2'):
                run_button = ui.button('执行程序', on_click=run_script, icon='play_circle', color='positive')
                stop_button = ui.button('结束任务', on_click=kill_running_script, icon='stop_circle', color='negative')

            def sync_ui_state():
                nonlocal last_line_sent
                if terminal.is_deleted:
                    timer.cancel()
                    return

                if len(GLOBAL_LOG_CONTENT) < last_line_sent:
                    terminal.clear()
                    last_line_sent = 0

                if len(GLOBAL_LOG_CONTENT) > last_line_sent:
                    new_lines = GLOBAL_LOG_CONTENT[last_line_sent:]
                    terminal.write('\r\n'.join(new_lines) + '\r\n')
                    last_line_sent = len(GLOBAL_LOG_CONTENT)

                if SCRIPT_PROCESS is None or SCRIPT_PROCESS.returncode is not None:
                    run_button.enable()
                    stop_button.disable()
                else:
                    run_button.disable()
                    stop_button.enable()

            timer = ui.timer(0.2, sync_ui_state)


kill_lingering_processes()
