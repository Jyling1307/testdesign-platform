import json
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from config import DATA_DIR
from schemas.knowledge import KnowledgeSearchRequest, KnowledgeSearchResult
from knowledge.embeddings import embed_query
from knowledge.chroma_service import KnowledgeService, get_collection, get_chroma_client
from rag.config import RAGConfig
from rag.ingestion.ingest_service import ingest_file, ingest_directory

router = APIRouter(prefix='/api/knowledge', tags=['knowledge'])


@router.post('/search/', response_model=list[KnowledgeSearchResult])
def search_knowledge(req: KnowledgeSearchRequest):
    query_embedding = embed_query(req.query)
    results = KnowledgeService.search(
        query_embedding,
        query_text=req.query,
        n_results=req.n_results,
        source_types=req.source_types or None,
        case_types=req.case_types or None,
        project=req.project or None,
        collection_name=req.collection or None,
        parent_doc=False,
    )
    return [
        KnowledgeSearchResult(
            content=r['text'],
            source=r['metadata'].get('source_title', ''),
            source_type=r['metadata'].get('source_type', ''),
            case_type=r['metadata'].get('case_type', ''),
            heading=r['metadata'].get('heading', r['metadata'].get('heading_context', '')),
            collection=r['collection'],
            score=round(1 - r['distance'], 4),
            rerank_score=round(1 - r['distance'], 4),
        )
        for r in results
    ]


# ============================================================
# 知识库管理 API（新增，配套 RAG 流程）
# ============================================================

@router.post('/ingest-directory/')
def ingest_directory_api(directory: str = Form(''), reset: bool = Form(False)):
    """批量入库目录下所有 .docx/.md/.json 文件到 knowledge_base collection。

    - .docx → 开发设计文档（source_type=design_doc）
    - .md → 历史测试设计（source_type=test_design）
    - .json → 代码图谱（source_type=code）

    流程：解析 → 术语标准化 → feature/spec 切分 → LLM 标签 → embedding → ChromaDB
    """
    directory = directory or str(Path(DATA_DIR) / 'knowledge')
    if not Path(directory).exists():
        raise HTTPException(404, f'目录不存在: {directory}')
    total = ingest_directory(directory, reset=reset)
    return {'total_nodes': total, 'directory': directory, 'collection': RAGConfig.COLLECTION}


@router.post('/ingest-file/')
async def ingest_file_api(file: UploadFile = File(...), source_type: str = Form('')):
    """上传单个文件入库（自动按扩展名分发：.docx/.md/.json）。"""
    content = await file.read()
    doc_id = Path(file.filename or 'upload').stem
    ext = Path(file.filename or '').suffix.lower()

    # 写临时文件
    with tempfile.NamedTemporaryFile(mode='wb', suffix=ext, delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        n = ingest_file(tmp_path, doc_id=doc_id)
        return {'filename': file.filename, 'doc_id': doc_id, 'nodes': n}
    except Exception as e:
        raise HTTPException(500, f'入库失败: {e}')
    finally:
        os.unlink(tmp_path)


@router.post('/ingest-code-graph/')
async def ingest_code_graph_api(file: UploadFile = File(...)):
    """上传代码图谱 JSON 文件入库。

    JSON 格式：{"modules": [{"module_name": "...", "file_path": "...",
              "functions": [{"name": "...", "operations": [...]}], "dependencies": [...]}]}
    """
    content = await file.read()
    try:
        data = json.loads(content)
    except Exception as e:
        raise HTTPException(400, f'JSON 解析失败: {e}')

    doc_id = Path(file.filename or 'code_graph').stem
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
        tmp_path = f.name
    try:
        n = ingest_file(tmp_path, doc_id=doc_id)
        return {'filename': file.filename, 'doc_id': doc_id, 'nodes': n}
    finally:
        os.unlink(tmp_path)


@router.get('/stats/')
def knowledge_stats():
    """知识库统计：各 collection 的节点数。"""
    stats = {}
    client = get_chroma_client()
    # 新 RAG 流程的 collection
    for col_name in [RAGConfig.COLLECTION]:
        try:
            col = client.get_collection(col_name)
            stats[col_name] = col.count()
        except Exception:
            stats[col_name] = 0
    # 旧 collection（testdesign 原有）
    for col_name in ['documents', 'test_patterns', 'parent_documents']:
        try:
            col = client.get_collection(col_name)
            stats[col_name] = col.count()
        except Exception:
            stats[col_name] = 0
    return stats


@router.delete('/entry/{vector_id}')
def delete_entry(vector_id: str):
    """删除指定向量 id 的知识条目（从 knowledge_base collection）。"""
    col = get_collection(RAGConfig.COLLECTION)
    try:
        col.delete(ids=[vector_id])
        return {'deleted': vector_id}
    except Exception as e:
        raise HTTPException(404, f'删除失败: {e}')


@router.post('/reset/')
def reset_knowledge_base():
    """清空 knowledge_base collection（重新全量入库前调用）。"""
    try:
        client = get_chroma_client()
        client.delete_collection(name=RAGConfig.COLLECTION)
        get_collection(RAGConfig.COLLECTION)  # 重建空 collection
        return {'status': 'reset', 'collection': RAGConfig.COLLECTION}
    except Exception as e:
        raise HTTPException(500, f'重置失败: {e}')
