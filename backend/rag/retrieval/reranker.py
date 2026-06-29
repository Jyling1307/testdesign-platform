"""Rerank 封装（从 langchain 迁移，调硅基流动 rerank API）。

用 API 替代本地 cross-encoder：省去下载 reranker 权重，也绕开 numpy/torch 兼容问题。
硅基流动 rerank 返回每个文档的 relevance_score，按分排序取 top_n。
"""
import requests

from rag.config import RerankerConfig


def rerank_documents(query: str, documents: list[str], top_n: int | None = None):
    """调硅基流动 rerank API 重排文档。

    Returns:
        [(document, score, idx), ...] 按分数降序，idx 为 documents 原始下标。
    """
    if not documents:
        return []
    n = top_n if top_n is not None else RerankerConfig.top_n
    try:
        resp = requests.post(
            f"{RerankerConfig.base_url}rerank",
            headers={"Authorization": f"Bearer {RerankerConfig.api_key}"},
            json={
                "model": RerankerConfig.model,
                "query": query,
                "documents": documents,
                "top_n": n,
                "return_documents": False,
            },
            timeout=RerankerConfig.timeout,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return [(documents[r["index"]], float(r["relevance_score"]), r["index"]) for r in results]
    except Exception:  # noqa: BLE001 rerank 失败降级：返回原始顺序前 n 个
        return [(doc, 0.0, idx) for idx, doc in enumerate(documents[:n])]
