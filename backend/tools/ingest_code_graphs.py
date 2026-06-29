"""批量入库代码图谱（fast 模式：跳过 splitter，节点数减半）。

代码图谱的 operation 节点（spec）已经是合适检索粒度，不需要 splitter 再产 feature 父。
直接入库 code_parser 输出，节点数 = module + operation（不翻倍）。

用法：
    python tools/ingest_code_graphs.py              # 入库 v5/mos_v6/om（v3 已入）
    python tools/ingest_code_graphs.py mos_v6 om     # 指定
"""
import sys
import time
from pathlib import Path

# 确保 backend/ 在 sys.path（脚本从 tools/ 运行时需要）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 加速 1：embedding batch 调大到 200
import knowledge.embeddings as emb_mod
_orig_embed = emb_mod.embed_texts
emb_mod.embed_texts = lambda texts, model=None, batch_size=200: _orig_embed(texts, model, batch_size)

# 加速 2：关 tagger（代码图谱 module 命名本身清晰，不需要 LLM 标签）
from rag.config import RAGConfig
RAGConfig.TAGGER_ENABLED = False

from rag.ingestion.parsers import code_parser
from rag.ingestion.indexer import ChromaIndexer

TARGETS = sys.argv[1:] if len(sys.argv) > 1 else ['v5', 'mos_v6', 'om']


def main():
    indexer = ChromaIndexer()
    print(f"=== fast 模式批量入库: {TARGETS} ===", flush=True)
    print(f"（跳过 splitter + tagger，batch=200，节点数 = module + operation）\n", flush=True)

    grand_total = 0
    for name in TARGETS:
        path = f'data/knowledge/code_graph_{name}.json'
        if not Path(path).exists():
            print(f"⚠️  [{name}] 文件不存在: {path}", flush=True)
            continue
        doc_id = f'code_{name}'
        print(f"[{name}] 入库 {path}...", flush=True)
        start = time.time()
        try:
            sections = code_parser.parse_code_graph(path, doc_id)
            indexer.add_nodes(sections)
            elapsed = time.time() - start
            grand_total += len(sections)
            print(f"  ✅ {len(sections)} 节点, {elapsed:.0f}s ({elapsed/60:.1f}min)", flush=True)
        except Exception as e:
            print(f"  ❌ 失败: {e}", flush=True)

    print(f"\n=== 全部完成: 新增 {grand_total} 节点 ===", flush=True)
    print(f"knowledge_base 当前总数: {indexer.count()}", flush=True)


if __name__ == '__main__':
    main()
