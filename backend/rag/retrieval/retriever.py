"""RAG 检索器（从 langchain 迁移）。

流程：query 打标签过滤 → 多问题检索聚合 → 父子合并（small-to-big）→ rerank 精排。
标签过滤过严导致无候选时，自动回退纯向量检索。
"""
from rag.config import RAGConfig
from knowledge.embeddings import embed_query
from rag.ingestion.indexer import ChromaIndexer
from rag.ingestion.tagger import tag_content
from rag.retrieval.reranker import rerank_documents


class RAGRetriever:
    def __init__(self):
        self.indexer = ChromaIndexer()

    def _query_spec(self, query: str, top_k: int, source_types: list[str] | None, tags: dict | None = None) -> dict:
        """单问题检索 spec 叶子。tags 非空时加标签过滤。"""
        q_emb = embed_query(query)
        clauses = [{"level": RAGConfig.LEVEL_SPEC}]
        if source_types:
            clauses.append({"source_type": {"$in": source_types}})
        if tags:
            for k, v in tags.items():
                if v:  # 空标签不过滤
                    clauses.append({f"tag_{k}": v})
        where = clauses[0] if len(clauses) == 1 else {"$and": clauses}
        return self.indexer.collection.query(query_embeddings=[q_emb], n_results=top_k, where=where)

    def _collect_candidates(self, queries, top_k, source_types, tags):
        """对多个 query 检索并聚合去重。"""
        candidates: list[tuple[str, dict, float]] = []
        seen_ids: set[str] = set()
        for q in queries:
            res = self._query_spec(q, top_k, source_types, tags)
            ids = (res.get("ids") or [[]])[0]
            docs = (res.get("documents") or [[]])[0]
            metas = (res.get("metadatas") or [[]])[0]
            dists = (res.get("distances") or [[]])[0]
            for cid, doc, meta, dist in zip(ids, docs, metas, dists):
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)
                candidates.append((doc, meta or {}, dist))
        return candidates, seen_ids

    def retrieve(
        self,
        queries: list[str],
        top_k: int | None = None,
        source_types: list[str] | None = None,
        rerank_query: str | None = None,
        use_tag_filter: bool = True,
    ):
        """多问题检索聚合 → 父子合并 → rerank。

        标签过滤：从首个 query 提标签过滤候选；过滤后无候选则回退纯向量。
        """
        top_k = top_k or RAGConfig.SIMILARITY_TOP_K

        # 从首个 query 提标签（代表性），用于过滤候选
        tags = {}
        if use_tag_filter and queries:
            tags = tag_content(queries[0])

        # 1. 多问题检索聚合
        candidates, _seen = self._collect_candidates(queries, top_k, source_types, tags)

        # 标签过滤过严无候选 → 回退纯向量
        if not candidates and tags and queries:
            candidates, _seen = self._collect_candidates(queries, top_k, source_types, {})

        if not candidates:
            return []

        # 2. 父子合并（small-to-big）
        parent_ids = [c[1].get("parent_id") for c in candidates if c[1].get("parent_id")]
        parents: dict[str, str] = {}
        if parent_ids:
            pres = self.indexer.get_by_ids(parent_ids)
            for pid, pdoc in zip(pres.get("ids", []), pres.get("documents", [])):
                parents[pid] = pdoc

        context_docs: list[str] = []
        context_metas: list[dict] = []
        for doc, meta, _dist in candidates:
            pid = meta.get("parent_id")
            combined = f"【上下文】{parents[pid]}\n【细节】{doc}" if (pid and pid in parents) else doc
            context_docs.append(combined)
            context_metas.append(meta)

        # 3. rerank 精排
        rq = rerank_query or (queries[0] if queries else "")
        reranked = rerank_documents(rq, context_docs, RAGConfig.RERANK_TOP_N)
        return [(doc, score, context_metas[idx]) for doc, score, idx in reranked]
