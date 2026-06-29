"""Parse .pdf files using PyPDF2."""


def parse_pdf(file_path):
    """Extract text from a .pdf file.

    Returns:
        tuple: (raw_text, parsed_structure)
    """
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    full_text_parts = []
    sections = []

    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            full_text_parts.append(text.strip())
            sections.append({
                'text': text.strip(),
                'style': 'Page',
                'level': 0,
            })

    raw_text = '\n'.join(full_text_parts)
    return raw_text, {'sections': sections}
