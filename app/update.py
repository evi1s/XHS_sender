import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import py_compile

REPO = 'evi1s/XHS_sender'
BRANCH = 'main'
APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(APP_DIR, '.update_state.json')
SKIP_FILES = {'config.py'}
INCLUDE_EXT = {'.py', '.json', '.jpg', '.jpeg', '.png', '.webp'}
RESTART_CMD = (
    "sleep 2; tmux kill-session -t nicegui 2>/dev/null; sleep 1; "
    "tmux new-session -d -s nicegui 'cd /root/nicegui && python nicegui_app.py'"
)


def _api(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'xhs-updater'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))


def _download(url, dest):
    req = urllib.request.Request(url, headers={'User-Agent': 'xhs-updater'})
    with urllib.request.urlopen(req, timeout=30) as r:
        with open(dest, 'wb') as f:
            shutil.copyfileobj(r, f)


def get_remote_state():
    data = _api('https://api.github.com/repos/%s/commits?path=app&per_page=1' % REPO)
    commit = data[0]
    return {
        'sha': commit['sha'],
        'message': commit['commit']['message'],
        'time': commit['commit']['committer']['date'],
    }


def get_local_state():
    try:
        with open(STATE_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def save_state(sha):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'sha': sha, 'checked_at': time.time()}, f)


def check_update():
    remote = get_remote_state()
    local = get_local_state()
    if local is None:
        save_state(remote['sha'])
        return None
    if local.get('sha') != remote['sha']:
        return remote
    return None


def list_app_files():
    data = _api('https://api.github.com/repos/%s/git/trees/%s?recursive=1' % (REPO, BRANCH))
    files = []
    for item in data.get('tree', []):
        p = item.get('path', '')
        if item.get('type') != 'blob' or not p.startswith('app/'):
            continue
        name = os.path.basename(p)
        if name in SKIP_FILES:
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext in INCLUDE_EXT:
            files.append(p)
    return sorted(files)


def do_update(dry_run=False):
    files = list_app_files()
    if not files:
        return False, '未获取到远程文件清单'
    tmpdir = tempfile.mkdtemp(prefix='xhs_upd_')
    try:
        for p in files:
            rel = p[len('app/'):]
            dest = os.path.join(tmpdir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            url = 'https://raw.githubusercontent.com/%s/%s/%s' % (REPO, BRANCH, p)
            try:
                _download(url, dest)
            except Exception as e:
                return False, '下载失败: %s: %s' % (rel, e)
        for p in files:
            rel = p[len('app/'):]
            dest = os.path.join(tmpdir, rel)
            if rel.endswith('.py'):
                try:
                    py_compile.compile(dest, doraise=True)
                except Exception as e:
                    return False, '语法校验失败: %s: %s' % (rel, e)
            elif rel.endswith('.json'):
                try:
                    json.load(open(dest, encoding='utf-8'))
                except Exception as e:
                    return False, 'JSON校验失败: %s: %s' % (rel, e)
        if dry_run:
            return True, '校验通过, 共 %d 个文件待更新' % len(files)
        bak = '/tmp/xhs_update_backup_%d.tar.gz' % int(time.time())
        try:
            with tarfile.open(bak, 'w:gz') as tf:
                for p in files:
                    rel = p[len('app/'):]
                    src = os.path.join(APP_DIR, rel)
                    if os.path.exists(src):
                        tf.add(src, arcname=rel)
        except Exception:
            pass
        for p in files:
            rel = p[len('app/'):]
            src = os.path.join(tmpdir, rel)
            dst = os.path.join(APP_DIR, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        remote = get_remote_state()
        save_state(remote['sha'])
        try:
            os.remove(bak)
        except Exception:
            pass
        return True, '更新完成: %d 个文件' % len(files)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def restart_nicegui():
    subprocess.Popen(['bash', '-c', RESTART_CMD])
