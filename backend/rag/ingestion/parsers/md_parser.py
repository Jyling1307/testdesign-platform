"""Markdown 解析器（用于历史测试设计文档入库，从 langchain 迁移）。

按 # 标题层级解析，每个标题段落产出 section 节点，逻辑与 docx_parser 对齐。
"""
import re

from rag.common.chunk import ChunkNode
from rag.config import RAGConfig

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def parse_md(path: str, doc_id: str, source_type: str = "test_design") -> list[ChunkNode]:
    """解析 markdown，返回 section 级 ChunkNode 列表。"""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    nodes: list[ChunkNode] = []
    path_stack: list[tuple[int, str]] = []
    buffer: list[str] = []
    seq = 0
    current_module_path = ""

    def flush():
        nonlocal buffer, seq
        text = "".join(buffer).strip()
        buffer = []
        if not text:
            return
        nodes.append(ChunkNode(
            content=text,
            level=RAGConfig.LEVEL_FEATURE,
            module_path=current_module_path,
            doc_id=doc_id,
            source_type=source_type,
            id=f"{doc_id}-s{seq}",
        ))
        seq += 1

    for line in lines:
        m = _HEADING_RE.match(line.strip())
        if m:
            flush()
            level = len(m.group(1))
            title = m.group(2).strip()
            path_stack = [(l, t) for (l, t) in path_stack if l < level]
            path_stack.append((level, title))
            current_module_path = "/".join(t for (_, t) in path_stack)
            nodes.append(ChunkNode(
                content=f"{'#' * level} {title}",
                level=RAGConfig.LEVEL_FEATURE,
                module_path=current_module_path,
                doc_id=doc_id,
                source_type=source_type,
                id=f"{doc_id}-h{seq}",
            ))
            seq += 1
        else:
            buffer.append(line)

    flush()
    return nodes
