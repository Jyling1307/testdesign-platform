"""Service to process uploaded documents: parent-child chunk, embed, store in ChromaDB."""

from sqlalchemy.orm import Session
from config import settings
from parsers.text_chunker import chunk_text_parent_child
from knowledge.chroma_service import KnowledgeService, delete_by_source
from knowledge.embeddings import embed_texts
from models.knowledge import KnowledgeEntry


def process_document_embedding(doc, db: Session = None):
    """Parent-child chunk, embed, and store in ChromaDB + DB.

    Args:
        doc: Document model instance with raw_text populated
        db: Optional SQLAlchemy session
    """
    if not doc.raw_text:
        return

    # Step 1: Parent-child chunking
    chunks = chunk_text_parent_child(doc.raw_text)
    if not chunks:
        doc.status = 'embedded'
        if db:
            db.commit()
        return

    # Step 2: Embed all child chunks
    texts = [c['text'] for c in chunks]
    embeddings = embed_texts(texts)

    # Step 3: Prepare metadata and IDs
    metadatas = []
    ids = []
    for c in chunks:
        meta = {
            'source_type': 'document',
            'source_id': str(doc.id),
            'source_title': doc.title,
            'project': str(doc.project_id) if doc.project_id else '',
            'chunk_index': str(c['index']),
            'heading': c.get('heading_context', ''),
            'parent_index': str(c['parent_index']),
            'parent_text': c['parent_text'],
        }
        metadatas.append(meta)
        ids.append(f"doc_{doc.id}_chunk_{c['index']}")

    # Step 4: Store child chunks in ChromaDB
    KnowledgeService.add_chunks('documents', texts, embeddings, metadatas, ids)

    # Step 5: Store unique parent chunks in parent_documents collection
    seen_parents = set()
    for c in chunks:
        pi = c['parent_index']
        if pi in seen_parents:
            continue
        seen_parents.add(pi)
        parent_id = f"doc_{doc.id}_parent_{pi}"
        parent_meta = {
            'source_type': 'document',
            'source_id': str(doc.id),
            'source_title': doc.title,
            'project': str(doc.project_id) if doc.project_id else '',
        }
        KnowledgeService.add_parent_document(parent_id, c['parent_text'], parent_meta)

    # Step 6: Create KnowledgeEntry records (if db provided)
    if db:
        for c in chunks:
            entry = KnowledgeEntry(
                project_id=doc.project_id,
                source_type='document',
                source_id=doc.id,
                chunk_text=c['text'],
                chunk_index=c['index'],
                vector_id=f"doc_{doc.id}_chunk_{c['index']}",
                metadata={'heading': c.get('heading_context', ''), 'parent_index': c['parent_index']},
            )
            db.add(entry)

    # Step 7: Update document status
    doc.status = 'embedded'
    if db:
        db.commit()
