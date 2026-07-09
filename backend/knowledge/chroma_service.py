"""ChromaDB operations for the knowledge base."""

import chromadb
from config import settings
from rag.config import RAGConfig


def get_chroma_client():
    """Get or create a persistent ChromaDB client."""
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)


def get_collection(name='documents'):
    """Get or create a ChromaDB collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(name=name)


def delete_by_source(collection_name, source_id_prefix):
    """Delete vectors whose ID starts with the given prefix.

    Useful for removing stale chunks when re-importing a document.
    """
    collection = get_collection(collection_name)
    try:
        existing = collection.get()
        ids_to_delete = [id_ for id_ in existing['ids'] if id_.startswith(source_id_prefix)]
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
        return len(ids_to_delete)
    except Exception:
        return 0


class KnowledgeService:
    @staticmethod
    def add_chunks(collection_name, chunks, embeddings, metadatas, ids):
        """Add chunks to a ChromaDB collection."""
        collection = get_collection(collection_name)
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch_end = min(i + batch_size, len(chunks))
            collection.add(
                documents=chunks[i:batch_end],
                embeddings=embeddings[i:batch_end],
                metadatas=metadatas[i:batch_end],
                ids=ids[i:batch_end],
            )

    @staticmethod
    def add_parent_document(parent_id, full_text, metadata, embedding=None):
        """Store a full parent document in the parent_documents collection.

        Args:
            parent_id: Unique ID (e.g. 'kb_xxx_parent' or 'design_42_parent')
            full_text: Complete document text
            metadata: dict with source_type, source_title, etc.
            embedding: Optional embedding vector. If None, uses a zero vector.
        """
        collection = get_collection('parent_documents')
        import numpy as np
        if embedding is None:
            # Parent docs are never searched; use a dummy embedding
            dim = 2048  # embedding-3 dimension
            embedding = np.zeros(dim).tolist()
        # Upsert to handle re-import
        existing = collection.get(ids=[parent_id])
        if existing['ids']:
            collection.update(
                ids=[parent_id],
                documents=[full_text],
                embeddings=[embedding],
                metadatas=[metadata],
            )
        else:
            collection.add(
                ids=[parent_id],
                documents=[full_text],
                embeddings=[embedding],
                metadatas=[metadata],
            )

    @staticmethod
    def get_parent_document(parent_id):
        """Fetch a parent document by ID from parent_documents collection."""
        collection = get_collection('parent_documents')
        try:
            result = collection.get(ids=[parent_id], include=['documents'])
            if result['documents']:
                return result['documents'][0]
            return ''
        except Exception:
            return ''

    @staticmethod
    def search(query_embedding, query_text='', collection_name=None, n_results=10, where=None,
               source_types=None, case_types=None, project=None, parent_doc=False):
        """Search across ChromaDB collections with metadata filtering.

        Args:
            query_embedding: Query vector
            query_text: Original query text (needed for rerank)
            collection_name: Specific collection to search (None = search both)
            n_results: Number of results to return
            where: Raw ChromaDB where filter dict
            source_types: Filter by source_type, e.g. ['testcase', 'design']
            case_types: Filter by case_type, e.g. ['功能测试', '性能基线测试']
            project: Filter by project ID string
            parent_doc: If True, return full parent documents (for AI context).
                        If False, return individual chunks (for UI display).

        Returns:
            list of dicts: [{text, metadata, distance, collection}]
        """
        client = get_chroma_client()

        # 共享条件：所有 collection 都生效（source_types / case_types / where）
        shared_conditions = []
        # project 条件仅对项目级 collection 生效，对全局知识库（knowledge_base）豁免
        project_condition = None

        if source_types:
            if len(source_types) == 1:
                shared_conditions.append({'source_type': source_types[0]})
            else:
                shared_conditions.append({'$or': [{'source_type': st} for st in source_types]})

        if case_types:
            if len(case_types) == 1:
                shared_conditions.append({'case_type': case_types[0]})
            else:
                shared_conditions.append({'$or': [{'case_type': ct} for ct in case_types]})

        if project:
            project_condition = {'project': str(project)}

        if where:
            shared_conditions.append(where)

        def _build_where(include_project: bool):
            conds = list(shared_conditions)
            if include_project and project_condition:
                conds.append(project_condition)
            if not conds:
                return None
            if len(conds) == 1:
                return conds[0]
            return {'$and': conds}

        # Determine which collections to search
        # knowledge_base（RAG 主库，含代码图谱/历史设计/历史测试设计）是全局共享，不绑 project
        if collection_name:
            cols = [(collection_name, collection_name == RAGConfig.COLLECTION)]
        else:
            cols = [
                ('documents', False),          # 项目级：project 过滤生效
                ('test_patterns', False),      # 项目级：project 过滤生效
                (RAGConfig.COLLECTION, True),  # 全局级：project 过滤豁免
            ]

        # Over-fetch for rerank (3x)
        fetch_n = n_results * 3 if settings.RERANK_ENABLED else n_results

        all_results = []
        for col_name, is_global in cols:
            try:
                collection = client.get_collection(col_name)
                kwargs = {
                    'query_embeddings': [query_embedding],
                    'n_results': fetch_n,
                }
                w = _build_where(include_project=not is_global)
                if w:
                    kwargs['where'] = w
                results = collection.query(**kwargs)
                for i, doc in enumerate(results['documents'][0]):
                    all_results.append({
                        'text': doc,
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i],
                        'collection': col_name,
                    })
            except Exception:
                continue

        # Sort by distance (lower is better)
        all_results.sort(key=lambda x: x['distance'])

        # Apply rerank if enabled
        if settings.RERANK_ENABLED and all_results and query_text:
            all_results = _rerank_results(all_results, query=query_text, top_n=n_results)

        # Parent document retrieval for AI context, or raw chunks for UI
        if parent_doc:
            return _build_parent_documents(all_results, n_results)

        return all_results[:n_results]


def _rerank_results(results, query, top_n=5):
    """Rerank search results using SiliconFlow rerank API.

    Uses POST {base_url}/rerank endpoint with the original query text.
    Falls back to original order if rerank fails.
    """
    try:
        import requests

        url = f'{settings.EMBEDDING_BASE_URL}rerank'
        headers = {
            'Authorization': f'Bearer {settings.EMBEDDING_API_KEY}',
            'Content-Type': 'application/json',
        }
        body = {
            'model': settings.RERANK_MODEL,
            'query': query,
            'documents': [r['text'] for r in results[:30]],
            'top_n': top_n,
            'return_documents': False,
        }
        resp = requests.post(url, headers=headers, json=body, timeout=10)
        data = resp.json()
        ranked = data['results']  # [{index, relevance_score}, ...]
        return [results[r['index']] for r in ranked]
    except Exception:
        return results[:top_n] if top_n < len(results) else results


def _build_parent_documents(results, n_results):
    """Replace child chunks with their parent chunks (Dify parent-child mode).

    - testcase entries are self-contained, kept as-is
    - Other types: deduplicate by (source_id, parent_index), return parent_text
    """
    parent_docs = []
    seen_parents = set()
    tc_count = 0

    for r in results:
        stype = r['metadata'].get('source_type', '')

        if stype == 'testcase':
            if tc_count >= n_results:
                continue
            parent_docs.append({
                'text': r['text'],
                'metadata': r['metadata'],
                'distance': r['distance'],
                'collection': r['collection'],
            })
            tc_count += 1
            continue

        source_id = r['metadata'].get('source_id', '')
        parent_idx = r['metadata'].get('parent_index', '')
        key = f"{source_id}_{parent_idx}"
        if key in seen_parents:
            continue
        seen_parents.add(key)

        parent_text = r['metadata'].get('parent_text', '')
        if parent_text:
            parent_docs.append({
                'text': parent_text,
                'metadata': r['metadata'],
                'distance': r['distance'],
                'collection': r['collection'],
            })

        if len(parent_docs) >= n_results:
            break

    return parent_docs
