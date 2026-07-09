#!/usr/bin/env python3
"""一键同步部署 testdesign-platform 到 20.20.20.19。

用法：python deploy.py

自动完成：前端构建 → 打包 backend → SFTP 上传 → 服务器解压 → 重启 uvicorn → 验证。
不动：chroma_db（知识库）、.env（配置）、已装依赖。
"""
import os
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

import paramiko

# ============ 服务器配置（从环境变量读取，或使用默认值） ============
SERVER = os.environ.get('DEPLOY_SERVER', '20.20.20.19')
USER = os.environ.get('DEPLOY_USER', 'root')
PASSWORD = os.environ.get('DEPLOY_PASSWORD', '')  # 必须通过环境变量设置
REMOTE_DIR = os.environ.get('DEPLOY_REMOTE_DIR', '/opt/testdesign')
APP_PORT = int(os.environ.get('DEPLOY_APP_PORT', '18000'))
PYTHON_BIN = os.environ.get('DEPLOY_PYTHON_BIN', '/usr/local/bin/python3.11')
LOCAL_PROJECT = os.environ.get('DEPLOY_LOCAL_PROJECT', r'D:\桌面\工作文档\testdesign-platform')
NODE_BIN = os.environ.get('DEPLOY_NODE_BIN', r'C:\Program Files\nodejs\node.exe')

EXCLUDE_DIRS = {'venv', '__pycache__', 'data', '.pytest_cache', 'backend.bak', '.git'}


def log(msg):
    print(msg, flush=True)


def ssh_exec(client, cmd, timeout=60):
    _, out, err = client.exec_command(cmd, timeout=timeout)
    return out.read().decode('utf-8', errors='replace').strip(), err.read().decode('utf-8', errors='replace').strip()


def build_frontend():
    """前端构建（vite build）。"""
    log('[1/5] 前端构建')
    frontend = Path('frontend')
    if not (frontend / 'src').exists():
        log('  跳过（无 frontend/src）')
        return True
    result = subprocess.run(
        [NODE_BIN, 'node_modules/vite/bin/vite.js', 'build'],
        cwd=str(frontend), capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0:
        log('  构建成功')
        return True
    log(f'  构建失败（继续用旧 dist）: {result.stderr[-150:]}')
    return False


def package():
    """打包 backend + frontend-dist，排除大目录。"""
    log('[2/5] 打包 backend + frontend-dist')
    pkg = 'deploy_update.tar.gz'
    # 刷新 frontend-dist
    if Path('frontend/dist').exists():
        if Path('frontend-dist').exists():
            shutil.rmtree('frontend-dist')
        shutil.copytree('frontend/dist', 'frontend-dist')

    with tarfile.open(pkg, 'w:gz') as tar:
        for root, dirs, files in os.walk('backend'):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                if f.endswith('.pyc') or f.endswith('.pyo'):
                    continue
                fp = os.path.join(root, f)
                tar.add(fp, arcname=fp.replace('\\', '/'))
        if Path('frontend-dist').exists():
            for root, dirs, files in os.walk('frontend-dist'):
                for f in files:
                    fp = os.path.join(root, f)
                    tar.add(fp, arcname=fp.replace('\\', '/'))
    size_kb = os.path.getsize(pkg) // 1024
    log(f'  打包完成 {size_kb}KB')
    return pkg


def upload_and_extract(client, pkg):
    """SFTP 上传 + 服务器解压。"""
    log('[3/5] SFTP 上传 + 解压')
    sftp = client.open_sftp()
    last = [0]

    def progress(transferred, total):
        pct = int(transferred / total * 100)
        if pct >= last[0] + 25:
            last[0] = pct
            log(f'  上传 {pct}%')

    sftp.put(pkg, f'{REMOTE_DIR}/{pkg}', callback=progress)
    log('  上传完成')
    sftp.close()

    o, e = ssh_exec(client, f'cd {REMOTE_DIR} && tar -xzf {pkg} && rm -f {pkg} && echo EXTRACT_OK')
    if 'EXTRACT_OK' in o:
        log('  解压 OK')
    else:
        log(f'  解压警告: {e[-150:]}')


def restart_server(client):
    """重启 uvicorn。"""
    log('[4/5] 重启 uvicorn')
    ssh_exec(client, 'pkill -9 -f "uvicorn main" 2>/dev/null; sleep 2')
    o, e = ssh_exec(client,
        f'cd {REMOTE_DIR}/backend && (setsid {PYTHON_BIN} -m uvicorn main:app '
        f'--host 0.0.0.0 --port {APP_PORT} > /var/log/testdesign.log 2>&1 < /dev/null &) '
        f'&& sleep 12 && echo RESTARTED', timeout=30)
    if 'RESTARTED' in o:
        log('  重启 OK')
    else:
        log(f'  重启信号异常（可能仍在启动）')


def verify(client):
    """验证服务。"""
    log('[5/5] 验证')
    time.sleep(3)
    o, e = ssh_exec(client, f'curl -s --max-time 10 http://localhost:{APP_PORT}/api/knowledge/stats/')
    log(f'  stats: {o}')
    o, e = ssh_exec(client, f'curl -s --max-time 5 http://localhost:{APP_PORT}/api/projects/')
    log(f'  projects: {o[:80]}')
    # 检查日志末尾有无错误
    o, e = ssh_exec(client, 'tail -3 /var/log/testdesign.log')
    if 'Error' in o or 'Traceback' in o:
        log(f'  日志疑似有错: {o[-150:]}')


def main():
    os.chdir(LOCAL_PROJECT)
    log(f'=== 同步部署 testdesign-platform → {SERVER}:{APP_PORT} ===\n')

    build_frontend()
    pkg = package()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SERVER, username=USER, password=PASSWORD, timeout=10)

    upload_and_extract(client, pkg)
    restart_server(client)
    verify(client)

    client.close()
    # 清理本地包
    pkg_path = Path(pkg)
    if pkg_path.exists():
        pkg_path.unlink()

    log('')
    log(f'=== 部署完成 ===')
    log(f'访问: http://{SERVER}:{APP_PORT}')
    log(f'日志: ssh {USER}@{SERVER} "tail -f /var/log/testdesign.log"')


if __name__ == '__main__':
    main()
