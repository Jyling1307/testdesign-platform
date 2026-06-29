"""入库编排：解析 → 术语标准化 → 切分 → 标签 → 入库（从 langchain 迁移）。

对外暴露 ingest_file / ingest_directory，供 API 和 CLI 调用。
按文件扩展名分发到对应 parser。
"""
import os
from pathlib import Path

from config import DATA_DIR

from rag.ingestion.glossary import extract_terms, standardize
from rag.ingestion.indexer import ChromaIndexer
from rag.ingestion.parsers import code_parser, docx_parser, md_parser
from rag.ingestion.splitter import split_to_leaf_nodes
from rag.ingestion.tagger import tag_nodes
from rag.config import RAGConfig

SUPPORTED_EXT = {".docx", ".md", ".json"}


def parse_file(path: str, doc_id: str):
    """按扩展名分发解析器，返回 section 级节点。"""
    ext = Path(path).suffix.lower()
    if ext == ".docx":
        return docx_parser.parse_docx(path, doc_id, source_type="design_doc")
    if ext == ".md":
        return md_parser.parse_md(path, doc_id, source_type="test_design")
    if ext == ".json":
        return code_parser.parse_code_graph(path, doc_id)
    return []


def apply_glossary(nodes) -> None:
    """对节点做术语标准化 + 提取术语标签（原地修改）。"""
    for n in nodes:
        n.content = standardize(n.content)
        n.terms = extract_terms(n.content)


def ingest_file(path: str, doc_id: str | None = None, indexer: ChromaIndexer | None = None) -> int:
    """单个文件入库一条龙，返回入库节点数。"""
    doc_id = doc_id or Path(path).stem
    indexer = indexer or ChromaIndexer()
    sections = parse_file(path, doc_id)
    apply_glossary(sections)
    all_nodes = split_to_leaf_nodes(sections)  # feature 父 + spec 叶子
    if RAGConfig.TAGGER_ENABLED:
        tag_nodes(all_nodes)  # feature 打标签，spec 继承
    indexer.add_nodes(all_nodes)
    return len(all_nodes)


def ingest_directory(directory: str | None = None, reset: bool = False) -> int:
    """批量入库目录下所有支持文件（docx/md/json）。"""
    directory = directory or str(Path(DATA_DIR) / "knowledge")
    indexer = ChromaIndexer()
    if reset:
        indexer.reset()

    files: list[str] = []
    for root, _dirs, fnames in os.walk(directory):
        for f in fnames:
            if Path(f).suffix.lower() in SUPPORTED_EXT:
                files.append(os.path.join(root, f))

    total = 0
    for fp in files:
        try:
            n = ingest_file(fp, indexer=indexer)
            total += n
            print(f"  ✅ {fp} → {n} 节点")
        except Exception as e:  # noqa: BLE001 单文件失败不中断整体
            print(f"  ❌ {fp} 失败：{e}")
    print(f"入库完成：共 {total} 节点，Chroma 当前 {indexer.count()} 节点")
    return total
