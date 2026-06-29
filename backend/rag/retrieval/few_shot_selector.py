"""历史测试设计 few-shot 精选（从 langchain 迁移）。

从 source_type=test_design 的历史用例库检索与 query 相关的优质片段，
作为生成时的 few-shot 示例，让 LLM 模仿本公司的写法风格与颗粒度。
"""
from rag.config import RAGConfig
from knowledge.embeddings import embed_query
from knowledge.chroma_service import get_collection


def select_few_shot(query: str, count: int | None = None) -> list[str]:
    """检索历史测试设计，返回 count 条文本作为 few-shot 示例。"""
    if not query:
        return []
    count = count or RAGConfig.FEW_SHOT_COUNT
    col = get_collection(RAGConfig.COLLECTION)
    q_emb = embed_query(query)
    where = {"$and": [{"source_type": "test_design"}, {"level": {"$in": ["feature", "spec"]}}]}
    try:
        res = col.query(query_embeddings=[q_emb], n_results=count, where=where)
        return res.get("documents", [[]])[0]
    except Exception:  # noqa: BLE001
        return []
