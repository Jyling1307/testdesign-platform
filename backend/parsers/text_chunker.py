"""Split document text into chunks for embedding."""

from config import settings


def chunk_text(text, chunk_size=None, overlap=None):
    """Split text into chunks, respecting paragraph boundaries.

    Args:
        text: Full document text
        chunk_size: Target chunk length in characters (default: from settings)
        overlap: Overlap between chunks in characters (default: from settings)

    Returns:
        list of dicts: [{text, index, heading_context}]
    """
    if chunk_size is None or overlap is None:
        chunk_size = chunk_size or settings.CHUNK_SIZE
        overlap = overlap or settings.CHUNK_OVERLAP

    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    chunks = []
    current_chunk = ''
    current_heading = ''

    for para in paragraphs:
        # Detect headings (short lines, no period at end)
        is_heading = len(para) < 100 and not para.endswith('。') and not para.endswith('.')
        if is_heading:
            current_heading = para

        if len(current_chunk) + len(para) > chunk_size:
            if current_chunk:
                chunks.append({
                    'text': current_chunk.strip(),
                    'heading_context': current_heading,
                })
                # Keep overlap: last N characters worth of sentences
                if overlap > 0:
                    words = current_chunk.split('。')
                    # Keep sentences until we reach overlap length
                    keep = []
                    for w in reversed(words):
                        candidate = '。'.join(keep + [w])
                        if len(candidate) > overlap and keep:
                            break
                        keep.insert(0, w)
                    overlap_text = '。'.join(keep)
                    if overlap_text and not overlap_text.endswith('。'):
                        overlap_text += '。'
                    current_chunk = overlap_text + para
                else:
                    current_chunk = para
            else:
                current_chunk = para
        else:
            current_chunk = current_chunk + '\n' + para if current_chunk else para

    if current_chunk.strip():
        chunks.append({
            'text': current_chunk.strip(),
            'heading_context': current_heading,
        })

    # Add index
    for i, chunk in enumerate(chunks):
        chunk['index'] = i

    return chunks


def chunk_text_parent_child(text, parent_size=None, parent_overlap=None, child_size=None, child_overlap=None):
    """Dify-style parent-child chunking.

    First splits into large parent chunks, then each parent into small child chunks.
    Only child chunks are embedded; parent chunks are stored for retrieval.

    Returns:
        list: [{text: child_text, index: child_index, parent_index, heading_context, parent_text}]
    """
    if parent_size is None:
        parent_size = settings.PARENT_CHUNK_SIZE
    if parent_overlap is None:
        parent_overlap = settings.PARENT_CHUNK_OVERLAP
    if child_size is None:
        child_size = settings.CHILD_CHUNK_SIZE
    if child_overlap is None:
        child_overlap = settings.CHILD_CHUNK_OVERLAP

    # Step 1: Split into parent chunks
    parent_chunks = chunk_text(text, chunk_size=parent_size, overlap=parent_overlap)

    # Step 2: Split each parent into child chunks
    child_chunks = []
    for pi, parent in enumerate(parent_chunks):
        children = chunk_text(parent['text'], chunk_size=child_size, overlap=child_overlap)
        for ci, child in enumerate(children):
            child_chunks.append({
                'text': child['text'],
                'index': len(child_chunks),  # global child index
                'parent_index': pi,
                'heading_context': child.get('heading_context', parent.get('heading_context', '')),
                'parent_text': parent['text'],
            })

    return child_chunks
