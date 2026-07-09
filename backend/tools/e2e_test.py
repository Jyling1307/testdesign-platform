"""E2E 测试：上传文档 → 创建设计 → AI 生成 → 删除设计 → 删除文档。
模拟前端完整流程，禁用代理直连本机后端。"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import websockets

# 禁用所有代理环境变量
for k in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    os.environ.pop(k, None)

BASE = 'http://127.0.0.1:8000'
WS_BASE = 'ws://127.0.0.1:8000'
DOC_PATH = 'D:/桌面/IDM V3支持分层带库2副本功能设计文档.md'


def main():
    s = requests.Session()
    s.trust_env = False

    # 1. 上传文档
    print('=' * 50)
    print('1. 上传 MD 文档')
    print('=' * 50)
    with open(DOC_PATH, 'rb') as f:
        r = s.post(f'{BASE}/api/documents/upload/1',
                   files={'file': (os.path.basename(DOC_PATH), f)}, timeout=300)
    assert r.status_code == 200, f'上传失败: {r.status_code} {r.text[:200]}'
    doc = r.json()
    doc_id = doc['id']
    print(f'  ✅ doc_id={doc_id}, title={doc["title"]}, status={doc["status"]}')

    # 2. 创建 testdesign
    print('\n' + '=' * 50)
    print('2. 创建测试设计')
    print('=' * 50)
    r = s.post(f'{BASE}/api/testdesigns/',
               json={'project_id': 1, 'document_id': doc_id}, timeout=10)
    assert r.status_code == 201, f'创建失败: {r.status_code} {r.text[:200]}'
    design = r.json()
    design_id = design['id']
    print(f'  ✅ design_id={design_id}, status={design["status"]}')

    # 3. 验证 GET 单个（之前斜杠 bug 修复点）
    r = s.get(f'{BASE}/api/testdesigns/{design_id}', timeout=10)
    assert r.status_code == 200 and r.json().get('id') == design_id, \
        f'GET 单个异常: {r.status_code} {r.headers.get("content-type")}'
    print(f'  ✅ GET /testdesigns/{design_id} 返回 JSON, id={r.json()["id"]}')

    # 4. WS AI 生成
    print('\n' + '=' * 50)
    print('3. WS AI 生成（选 功能测试 + 可靠性测试）')
    print('=' * 50)
    asyncio.run(ws_generate(design_id))


async def ws_generate(design_id):
    t0 = time.time()
    chunks = 0
    full_md = ''
    test_types = ['功能测试', '可靠性测试']
    async with websockets.connect(f'{WS_BASE}/ws/gen/{design_id}',
                                   open_timeout=30, close_timeout=30,
                                   ping_interval=None, ping_timeout=None,
                                   max_size=None) as ws:
        await ws.send(json.dumps({'notes': '', 'test_types': test_types}))
        async for msg in ws:
            data = json.loads(msg)
            t = data.get('type')
            if t == 'status':
                print(f'  [{time.time()-t0:5.1f}s] 📣 {data["message"]}')
            elif t == 'chunk':
                chunks += 1
                full_md += data.get('content', '')
                if chunks % 100 == 0:
                    print(f'  [{time.time()-t0:5.1f}s]   ... 已收 {chunks} chunk, {len(full_md)} 字')
            elif t == 'done':
                print(f'  [{time.time()-t0:5.1f}s] ✅ done')
                break
            elif t == 'error':
                print(f'  [error] {data.get("message")}')
                return
    print(f'\n  生成结果: {chunks} chunk, {len(full_md)} 字, 耗时 {time.time()-t0:.1f}s')
    print(f'  MD 预览（前 300 字）:\n{full_md[:300]}...')

    # 5. 删除 design（含本次 + 之前残留）
    print('\n' + '=' * 50)
    print('4. 删除测试设计')
    print('=' * 50)
    s = requests.Session(); s.trust_env = False
    r = s.get(f'{BASE}/api/testdesigns/?project=1', timeout=5)
    for d in r.json():
        r2 = s.delete(f'{BASE}/api/testdesigns/{d["id"]}', timeout=10)
        print(f'  DELETE design {d["id"]} → {r2.status_code} {"✅" if r2.status_code == 204 else "❌"}')

    # 6. 删除 document
    print('\n' + '=' * 50)
    print('5. 删除文档')
    print('=' * 50)
    r = s.get(f'{BASE}/api/documents/?project=1', timeout=5)
    docs = r.json()
    # 文档可能因删 design 被级联删，遍历删除剩余的
    for d in docs:
        if '2副本' in d.get('title', ''):
            r2 = s.delete(f'{BASE}/api/documents/{d["id"]}', timeout=10)
            print(f'  DELETE doc {d["id"]} ({d["title"][:30]}) → {r2.status_code} '
                  f'{"✅" if r2.status_code == 204 else "❌"}')

    # 7. 验证清理
    print('\n' + '=' * 50)
    print('验证清理结果')
    print('=' * 50)
    r = s.get(f'{BASE}/api/testdesigns/?project=1', timeout=5)
    print(f'  remaining designs: {len(r.json())}')
    r = s.get(f'{BASE}/api/documents/?project=1', timeout=5)
    print(f'  remaining docs: {len(r.json())}')
    print('\n🎉 E2E 测试完成！')


if __name__ == '__main__':
    main()
