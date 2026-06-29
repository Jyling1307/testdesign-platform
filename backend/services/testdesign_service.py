"""Service layer for test design generation: orchestrate context retrieval + LLM calls."""

from sqlalchemy.orm import Session

from knowledge.chroma_service import KnowledgeService
from knowledge.embeddings import embed_query
from llm.client import stream_chat, chat
from llm.prompts.generate_design import build_generate_prompt
from llm.prompts.refine_design import build_refine_prompt


def collect_kb_context(project_id, document_text, max_results=5,
                       source_types=None, case_types=None):
    """Collect relevant test patterns from knowledge base.

    Returns parent documents (full source text) instead of chunks,
    so the AI receives complete context for generation.

    Args:
        project_id: Project ID to scope search
        document_text: Document text (use first 500 chars as query seed)
        max_results: Max KB results
        source_types: Filter by source type, e.g. ['testcase', 'design']
        case_types: Filter by case type, e.g. ['功能测试']

    Returns:
        str: Formatted context string
    """
    if not document_text:
        return ''

    # Use first paragraph as seed query
    seed = document_text[:500]
    try:
        query_embedding = embed_query(seed)
        results = KnowledgeService.search(
            query_embedding,
            query_text=seed,
            n_results=max_results,
            source_types=source_types, case_types=case_types,
            parent_doc=True,
        )
        if not results:
            return ''

        context_parts = []
        for r in results:
            title = r['metadata'].get('source_title', '未知来源')
            text = r['text']
            if len(text) > 2000:
                text = text[:2000] + '\n...(内容过长已截断)'
            context_parts.append(f"【{title}】\n{text}")

        return '\n\n'.join(context_parts)
    except Exception:
        return ''


def generate_test_design_sync(design, db: Session, test_types=None):
    """Synchronous full generation: returns complete markdown.

    Args:
        design: TestDesign instance (must have document with raw_text)
        db: SQLAlchemy session
        test_types: Optional list of test types to generate

    Returns:
        str: Complete test design markdown
    """
    doc = design.document
    document_text = doc.raw_text or ''

    # Collect KB context
    kb_context = collect_kb_context(design.project_id, document_text)

    # Build prompt
    system_prompt, user_message = build_generate_prompt(
        document_text=document_text,
        kb_context=kb_context,
        test_types=test_types,
    )

    # Call LLM
    full_response = chat(system_prompt, user_message)

    # Save to design
    design.full_md = full_response
    design.status = 'reviewing'
    db.commit()

    return full_response


def refine_test_design_sync(design, db: Session, feedback_text, rejected_nodes=None, test_types=None):
    """Synchronous refinement based on user feedback.

    Args:
        design: TestDesign instance with full_md
        db: SQLAlchemy session
        feedback_text: User feedback
        rejected_nodes: List of rejected node dicts
        test_types: Optional list of test types to include

    Returns:
        str: Refined test design markdown
    """
    system_prompt, user_message = build_refine_prompt(
        current_md=design.full_md,
        rejected_nodes=rejected_nodes,
        feedback_text=feedback_text,
        test_types=test_types,
    )

    full_response = chat(system_prompt, user_message)

    design.full_md = full_response
    design.version += 1
    design.status = 'reviewing'
    db.commit()

    return full_response
