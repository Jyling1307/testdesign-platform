"""从代码图谱挖掘高频术语，生成中英对照词库。

策略：预设存储/IDM 领域中英候选，用 chroma get 验证英文术语在 code 条目的命中数，
命中数达标的写入 data/glossary/code_terms.json。
"""
import json
import sys
from pathlib import Path

# 把 backend 根目录加入 sys.path，让 import config 能生效
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from config import DATA_DIR, settings

# 存储/对象存储/IDM 领域候选术语 (英文, 中文, 同义词扩展)
CANDIDATES = [
    ('bucket', '桶', ['bucket_quota']),
    ('quota', '配额', []),
    ('object', '对象', ['object_storage']),
    ('gateway', '网关', ['object_gateway']),
    ('snapshot', '快照', []),
    ('volume', '卷', []),
    ('cluster', '集群', ['multi_cluster']),
    ('user', '用户', ['user_manage']),
    ('folder', '目录', ['sub_folder']),
    ('share', '共享', ['sub_dir_share']),
    ('archive', '归档', ['archive_mode']),
    ('tier', '分层', ['tiering']),
    ('replication', '副本', ['replica', 'dual_copy']),
    ('sync', '同步', ['async_sync']),
    ('backup', '备份', []),
    ('pool', '存储池', ['storage_pool']),
    ('namespace', '命名空间', []),
    ('metadata', '元数据', []),
    ('lifecycle', '生命周期', []),
    ('tenant', '租户', []),
    ('organization', '组织', ['org']),
    ('role', '角色', []),
    ('policy', '策略', []),
    ('qos', '服务质量', ['qos_policy']),
    ('bandwidth', '带宽', []),
    ('throughput', '吞吐', []),
    ('latency', '延迟', []),
    ('cache', '缓存', ['mcache']),
    ('flush', '刷盘', ['dirty_flush']),
    ('auth', '认证', []),
    ('permission', '权限', []),
    ('ceph', 'ceph', []),
    ('rados', 'rados', []),
    ('nfs', 'nfs', ['nfs_share']),
    ('cifs', 'cifs', ['cifs_share']),
    ('sftp', 'sftp', []),
    ('ftp', 'ftp', []),
    ('copy', '拷贝', ['copy_data']),
    ('migrate', '迁移', ['migration']),
    ('rebuild', '重建', ['rebuild_task']),
    ('rebalance', '重平衡', []),
    ('degrade', '降级', []),
    ('failover', '故障切换', []),
    ('health', '健康检查', ['health_check']),
    ('drive', '驱动', ['driver']),
    ('tape', '磁带', ['tape_lib']),
    ('media', '介质', ['media_pool']),
    ('encryption', '加密', ['encrypt']),
    ('event', '事件', []),
    ('alarm', '告警', ['alert']),
    ('log', '日志', []),
    ('audit', '审计', []),
    ('config', '配置', []),
    ('domain', '域', ['fault_domain']),
    ('zone', '区域', []),
    ('node', '节点', []),
    ('erasure', '纠删', ['erasure_code']),
    ('write', '写', []),
    ('read', '读', []),
]

THRESHOLD = 30  # 命中数 >= 此值才进词库
VERIFY_LIMIT = 2000  # 验证时最多取多少条


def main():
    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    kb = client.get_collection('knowledge_base')

    results = []
    for en, zh, extra in CANDIDATES:
        try:
            r = kb.get(where={'source_type': 'code'},
                       where_document={'$contains': en},
                       limit=VERIFY_LIMIT, include=[])
            cnt = len(r['ids'])
        except Exception as e:
            cnt = -1
        results.append((en, zh, extra, cnt))

    results.sort(key=lambda x: x[3], reverse=True)

    print('=== 候选术语命中统计 ===')
    glossary = {}
    for en, zh, extra, cnt in results:
        if cnt >= THRESHOLD:
            flag = '✅'
            # 中文术语为 key，synonyms 包含英文 + 扩展词
            syns = [en] + extra
            glossary[zh] = {'synonyms': syns, 'en': en}
        elif cnt >= 10:
            flag = '🟡'
        else:
            flag = '❌'
        print(f'  {flag} {en:18s} → {zh:8s}  命中 {cnt}')

    print(f'\n=== 进词库的术语数: {len(glossary)} (阈值 {THRESHOLD}) ===')

    # 写入 data/glossary/code_terms.json
    out_dir = Path(DATA_DIR) / 'glossary'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / 'code_terms.json'
    # 词库格式参考 glossary.py: {术语: {synonyms: [...]}}
    # 去掉临时的 'en' 字段（glossary.standardize 只用 synonyms）
    output = {k: {'synonyms': v['synonyms']} for k, v in glossary.items()}
    out_file.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'词库已写入: {out_file}')
    print(f'\n词库预览:')
    print(json.dumps(output, ensure_ascii=False, indent=2)[:800])


if __name__ == '__main__':
    main()
