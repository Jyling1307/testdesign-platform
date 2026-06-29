"""层级切分器（从 langchain 迁移）。

策略（两阶段）：
1. 结构化粗切已由 parser 完成（按 Heading 得到 feature 级 section）；
2. 这里对超长 section 用「中文分句 + 滑动窗口重叠」二次切，产出 spec 叶子。

📌 调优点在 rag/config.py 的 RAGConfig。
"""
import re

from rag.common.chunk import ChunkNode
from rag.config import RAGConfig


def _chinese_sentences(text: str) -> list[str]:
    """中文分句器。"""
    sents = re.findall(r"[^。！？；\n]+[。！？；\n]?", text)
    return [s.strip() for s in sents if s.strip()]


def _slide_window(sentences: list[str], max_chars: int, overlap_ratio: float) -> list[str]:
    """句子序列 → 滑动窗口块，相邻块带 overlap 字符重叠。"""
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    overlap = int(max_chars * overlap_ratio)
    for s in sentences:
        if cur and cur_len + len(s) > max_chars:
            chunks.append("".join(cur))
            keep: list[str] = []
            keep_len = 0
            for prev in reversed(cur):
                if keep_len + len(prev) > overlap:
                    break
                keep.insert(0, prev)
                keep_len += len(prev)
            cur = keep
            cur_len = sum(len(x) for x in cur)
        cur.append(s)
        cur_len += len(s)
    if cur:
        chunks.append("".join(cur))
    return chunks


def _make_leaf(content: str, parent: ChunkNode) -> ChunkNode:
    return ChunkNode(
        content=content,
        level=RAGConfig.LEVEL_SPEC,
        parent_id=parent.id,
        module_path=parent.module_path,
        doc_id=parent.doc_id,
        source_type=parent.source_type,
        node_type=parent.node_type,
        terms=list(parent.terms),
    )


def split_to_leaf_nodes(sections: list[ChunkNode]) -> list[ChunkNode]:
    """section(feature) 节点 → [原 section 父, spec 叶子...] 合并列表。"""
    max_chars = RAGConfig.CHUNK_SIZES[2] * 3  # 叶子字符上限（token×3 近似中文）
    split_threshold = RAGConfig.MAX_CHUNK_TOKENS
    result: list[ChunkNode] = []

    for sec in sections:
        result.append(sec)  # feature 父节点保留入库
        if len(sec.content) <= split_threshold:
            result.append(_make_leaf(sec.content, sec))
        else:
            for chunk_text in _slide_window(
                _chinese_sentences(sec.content), max_chars, RAGConfig.OVERLAP_RATIO
            ):
                if chunk_text.strip():
                    result.append(_make_leaf(chunk_text, sec))
    return result
