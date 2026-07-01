from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from deps import get_db
from models.document import Document
from schemas.document import DocumentResponse, DocumentCreate
from config import MEDIA_DIR

router = APIRouter(prefix='/api/documents', tags=['documents'])


@router.get('/', response_model=list[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.created_at.desc()).all()


@router.post('/', response_model=DocumentResponse, status_code=201)
def create_document(data: DocumentCreate, db: Session = Depends(get_db)):
    doc = Document(**data.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get('/{doc_id}', response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, '文档不存在')
    return doc


@router.put('/{doc_id}', response_model=DocumentResponse)
def update_document(doc_id: int, data: DocumentCreate, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, '文档不存在')
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(doc, k, v)
    db.commit()
    db.refresh(doc)
    return doc


@router.delete('/{doc_id}', status_code=204)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, '文档不存在')
    db.delete(doc)
    db.commit()


@router.post('/upload/{project_id}', response_model=DocumentResponse)
async def upload_document(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a document, parse it, and prepare for embedding."""
    import os
    import uuid

    # Validate file type
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ('docx', 'pdf', 'md'):
        raise HTTPException(400, '仅支持 .docx、.pdf 和 .md 文件')

    # Save file
    file_dir = MEDIA_DIR / 'documents'
    file_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = file_dir / file_name
    content = await file.read()
    with open(file_path, 'wb') as f:
        f.write(content)

    # Parse document
    raw_text = ''
    parsed_structure = {}
    if ext == 'docx':
        from parsers.docx_parser import parse_docx
        raw_text, parsed_structure = parse_docx(str(file_path))
    elif ext == 'pdf':
        from parsers.pdf_parser import parse_pdf
        raw_text, parsed_structure = parse_pdf(str(file_path))
    elif ext == 'md':
        # Markdown 解析：全文作 raw_text，按 # 标题层级产 parsed_structure
        raw_text = content.decode('utf-8', errors='ignore')
        parsed_structure = []
        for line in raw_text.split('\n'):
            stripped = line.strip()
            if stripped.startswith('#'):
                level = len(stripped) - len(stripped.lstrip('#'))
                parsed_structure.append({'text': stripped, 'style': f'Heading{level}', 'level': level})
            elif stripped:
                parsed_structure.append({'text': stripped, 'style': 'Normal', 'level': 0})

    # Create DB record
    doc = Document(
        project_id=project_id,
        title=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        file_type=ext,
        raw_text=raw_text,
        parsed_structure=parsed_structure,
        status='parsed',
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Trigger embedding in background (non-blocking for response)
    try:
        from services.document_service import process_document_embedding
        process_document_embedding(doc)
    except Exception:
        pass

    return doc
