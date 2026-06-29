"""docx 解析器（从 langchain 迁移）。

要点：
1. python-docx 解析，不走 OCR（docx 是结构化 Open XML）；
2. 读 paragraph.style.name 识别 Heading 1/2/3，重建层级 → module_path；
3. 按 body 顺序遍历，段落和表格不丢顺序；
4. 表格整体作为一个独立节点（node_type=table），绝不让 splitter 切碎表格；
5. 每个 Heading 段落产出一个 feature 级 section 节点（作为 spec 的父，回溯上下文用）。
"""
from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from rag.common.chunk import ChunkNode
from rag.config import RAGConfig

# Heading 样式名 → 层级（兼容中英文模板）
_HEADING_MAP = {
    "heading 1": 1, "heading 2": 2, "heading 3": 3, "heading 4": 4, "heading 5": 5,
    "标题 1": 1, "标题 2": 2, "标题 3": 3, "标题 4": 4, "标题 5": 5,
}


def _heading_level(style_name: str) -> int | None:
    return _HEADING_MAP.get((style_name or "").strip().lower())


def _iter_block_items(doc):
    """按文档顺序遍历段落和表格（python-docx 官方推荐写法）。"""
    body = doc.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, doc)
        elif isinstance(child, CT_Tbl):
            yield Table(child, doc)


def _table_to_markdown(table: Table) -> str:
    """表格转 markdown 字符串（整体作为一个节点存储）。"""
    rows = []
    for row in table.rows:
        cells = [c.text.strip().replace("\n", " ") for c in row.cells]
        rows.append("| " + " | ".join(cells) + " |")
    if rows:
        col_count = rows[0].count("|") - 1
        rows.insert(1, "| " + " | ".join(["---"] * col_count) + " |")
    return "\n".join(rows)


def parse_docx(path: str, doc_id: str, source_type: str = "design_doc") -> list[ChunkNode]:
    """解析 docx，返回 ChunkNode 列表（section 级，待 splitter 切分）。"""
    doc = Document(path)
    nodes: list[ChunkNode] = []
    path_stack: list[tuple[int, str]] = []
    buffer: list[str] = []
    seq = 0
    current_module_path = ""

    def flush_section():
        nonlocal buffer, seq
        text = "\n".join(buffer).strip()
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

    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue
            level = _heading_level(block.style.name)
            if level:
                flush_section()
                path_stack = [(l, t) for (l, t) in path_stack if l < level]
                path_stack.append((level, text))
                current_module_path = "/".join(t for (_, t) in path_stack)
                nodes.append(ChunkNode(
                    content=f"{'#' * level} {text}",
                    level=RAGConfig.LEVEL_FEATURE,
                    module_path=current_module_path,
                    doc_id=doc_id,
                    source_type=source_type,
                    id=f"{doc_id}-h{seq}",
                ))
                seq += 1
            else:
                buffer.append(text)
        elif isinstance(block, Table):
            flush_section()
            nodes.append(ChunkNode(
                content=_table_to_markdown(block),
                level=RAGConfig.LEVEL_FEATURE,
                module_path=current_module_path,
                doc_id=doc_id,
                source_type=source_type,
                node_type="table",
                id=f"{doc_id}-t{seq}",
            ))
            seq += 1

    flush_section()
    return nodes
