"""Knowledge accumulation: auto-embed approved designs and test cases into ChromaDB."""

from sqlalchemy.orm import Session

from knowledge.chroma_service import KnowledgeService, delete_by_source
from knowledge.embeddings import embed_texts
from parsers.text_chunker import chunk_text_parent_child
from models.knowledge import KnowledgeEntry


def embed_approved_design(design, db: Session):
    """Embed an approved test design into the test_patterns collection.

    Uses parent-child chunking for the design markdown.
    Also extracts test cases from step2 and embeds them with case_type metadata.

    Returns:
        tuple: (design_chunk_count, testcase_count)
    """
    if not design.full_md:
        return 0, 0

    design_chunk_count = 0

    # 1. Embed design markdown chunks using parent-child chunking (source_type='design')
    chunks = chunk_text_parent_child(design.full_md)

    if chunks:
        texts = [c['text'] for c in chunks]
        embeddings = embed_texts(texts)

        metadatas = []
        ids = []
        for c in chunks:
            metadatas.append({
                'source_type': 'design',
                'source_id': str(design.id),
                'source_title': design.document.title if design.document else '',
                'project': str(design.project_id) if design.project_id else '',
                'chunk_index': str(c['index']),
                'heading': c.get('heading_context', ''),
                'parent_index': str(c['parent_index']),
                'parent_text': c['parent_text'],
            })
            ids.append(f"design_{design.id}_chunk_{c['index']}")

        # Clean up old vectors for this design before re-adding
        delete_by_source('test_patterns', f"design_{design.id}_")
        delete_by_source('test_patterns', f"testcase_{design.id}_")

        KnowledgeService.add_chunks('test_patterns', texts, embeddings, metadatas, ids)

        # Store unique parent chunks in parent_documents collection
        seen_parents = set()
        for c in chunks:
            pi = c['parent_index']
            if pi in seen_parents:
                continue
            seen_parents.add(pi)
            parent_id = f"design_{design.id}_parent_{pi}"
            parent_meta = {
                'source_type': 'design',
                'source_id': str(design.id),
                'source_title': design.document.title if design.document else '',
                'project': str(design.project_id) if design.project_id else '',
            }
            KnowledgeService.add_parent_document(parent_id, c['parent_text'], parent_meta)

        # Delete old and create new KnowledgeEntry records
        db.query(KnowledgeEntry).filter(
            KnowledgeEntry.source_type == 'design',
            KnowledgeEntry.source_id == design.id,
        ).delete()
        for c in chunks:
            entry = KnowledgeEntry(
                project_id=design.project_id,
                source_type='design',
                source_id=design.id,
                chunk_text=c['text'],
                chunk_index=c['index'],
                vector_id=f"design_{design.id}_chunk_{c['index']}",
                metadata={'heading': c.get('heading_context', ''), 'parent_index': c['parent_index']},
            )
            db.add(entry)
        db.commit()

        design_chunk_count = len(chunks)

    # 2. Extract test cases from step2 and embed (source_type='testcase')
    testcase_count = embed_test_cases_from_md(design, db)

    return design_chunk_count, testcase_count


def embed_test_cases_from_md(design, db: Session):
    """Parse step2 of design MD and embed test cases with case_type metadata.

    Testcase entries are self-contained (no parent-child chunking).

    Returns:
        int: Number of test cases embedded
    """
    from parsers.md_parser import extract_step2, parse_step2_to_cases

    if not design.full_md:
        return 0

    product = design.project.product if design.project and design.project.product else ''
    step2_text = extract_step2(design.full_md)
    cases = parse_step2_to_cases(step2_text, product)

    if not cases:
        return 0

    return _embed_testcase_list(design, cases, db)


def embed_test_cases_from_parsed(design, cases, db: Session):
    """Embed parsed case dicts (from xlsx or other source) into test_patterns.

    Args:
        design: TestDesign instance
        cases: list of dicts with keys: name, product, case_type, phase,
               precondition, steps, expected
        db: SQLAlchemy session

    Returns:
        int: Number of test cases embedded
    """
    if not cases:
        return 0

    return _embed_testcase_list(design, cases, db)


def embed_test_cases(design, db: Session):
    """Embed parsed test cases into the test_patterns collection.

    Called when xlsx export happens (cases have been generated from DB TestCase objects).
    """
    from models.testcase import TestCase

    tcs = db.query(TestCase).filter(TestCase.test_design_id == design.id).all()
    if not tcs:
        return

    cases = [
        {
            'name': tc.name,
            'case_type': tc.case_type,
            'precondition': tc.precondition,
            'steps': tc.steps,
            'expected': tc.expected_result,
        }
        for tc in tcs
    ]
    _embed_testcase_list(design, cases, db)


def _embed_testcase_list(design, cases, db: Session):
    """Common helper to embed a list of testcase dicts into test_patterns.

    Args:
        design: TestDesign instance
        cases: list of dicts with keys: name, case_type, precondition, steps, expected
        db: SQLAlchemy session

    Returns:
        int: Number of test cases embedded
    """
    if not cases:
        return 0

    texts = []
    metadatas = []
    ids = []

    for i, case in enumerate(cases):
        case_text = (
            f"用例: {case['name']}\n"
            f"前置条件: {case['precondition']}\n"
            f"步骤: {case['steps']}\n"
            f"预期结果: {case['expected']}"
        )
        texts.append(case_text)
        metadatas.append({
            'source_type': 'testcase',
            'source_id': str(design.id),
            'source_title': design.document.title if design.document else '',
            'project': str(design.project_id) if design.project_id else '',
            'case_name': case['name'],
            'case_type': case['case_type'],
        })
        ids.append(f"testcase_{design.id}_case_{i}")

    embeddings = embed_texts(texts)

    # Clean up old testcase vectors for this design
    delete_by_source('test_patterns', f"testcase_{design.id}_")
    KnowledgeService.add_chunks('test_patterns', texts, embeddings, metadatas, ids)

    # Delete old and create new KnowledgeEntry records
    db.query(KnowledgeEntry).filter(
        KnowledgeEntry.source_type == 'testcase',
        KnowledgeEntry.source_id == design.id,
    ).delete()
    for i, case in enumerate(cases):
        entry = KnowledgeEntry(
            project_id=design.project_id,
            source_type='testcase',
            source_id=design.id,
            chunk_text=texts[i],
            chunk_index=i,
            vector_id=f"testcase_{design.id}_case_{i}",
            metadata={'case_name': case['name'], 'case_type': case['case_type']},
        )
        db.add(entry)
    db.commit()

    return len(cases)
