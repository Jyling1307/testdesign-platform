"""Chroma 入库器（从 langchain 迁移，父子靠 metadata 实现）。

设计：feature 父节点和 spec 叶子节点都存同一 collection（都带 embedding），
检索时用 where={"level": "spec"} 只查叶子；命中后通过 metadata.parent_id
按 id 取回父节点内容，组装完整上下文（small-to-big）。
"""
from rag.common.chunk import ChunkNode
from knowledge.embeddings import embed_texts
from knowledge.chroma_service import get_chroma_client, get_collection
from rag.config import RAGConfig


class ChromaIndexer:
    def __init__(self, collection_name: str | None = None):
        col_name = collection_name or RAGConfig.COLLECTION
        self.collection = get_collection(col_name)

    def add_nodes(self, nodes: list[ChunkNode], batch_size: int = 64) -> None:
        """批量入库。embedding 自己算后传入，精准控制、便于排查。"""
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i : i + batch_size]
            texts = [n.content for n in batch]
            embeddings = embed_texts(texts)
            self.collection.add(
                ids=[n.id for n in batch],
                embeddings=embeddings,
                documents=texts,
                metadatas=[n.to_metadata() for n in batch],
            )

    def get_by_ids(self, ids: list[str]) -> dict:
        """按 id 批量取回节点（父子回溯上下文用）。"""
        if not ids:
            return {"ids": [], "documents": [], "metadatas": []}
        return self.collection.get(ids=list(dict.fromkeys(ids)))  # 去重保序

    def count(self) -> int:
        return self.collection.count()

    def reset(self) -> None:
        """清空 collection（重新全量入库前调用）。"""
        name = self.collection.name
        get_chroma_client().delete_collection(name=name)
        self.collection = get_collection(name)
