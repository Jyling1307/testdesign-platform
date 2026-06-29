from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from deps import get_db
from models.testdesign import TestDesign, DesignReview
from schemas.testdesign import (
    TestDesignResponse,
    TestDesignCreate,
    ReviewItem,
    RefineRequest,
    SyncKBRequest,
)
from config import MEDIA_DIR

router = APIRouter(prefix='/api/testdesigns', tags=['testdesigns'])


@router.get('/', response_model=list[TestDesignResponse])
def list_testdesigns(db: Session = Depends(get_db)):
    return db.query(TestDesign).order_by(TestDesign.updated_at.desc()).all()


@router.post('/', response_model=TestDesignResponse, status_code=201)
def create_testdesign(data: TestDesignCreate, db: Session = Depends(get_db)):
    design = TestDesign(**data.model_dump())
    db.add(design)
    db.commit()
    db.refresh(design)
    return design


@router.get('/{design_id}', response_model=TestDesignResponse)
def get_testdesign(design_id: int, db: Session = Depends(get_db)):
    design = db.get(TestDesign, design_id)
    if not design:
        raise HTTPException(404, '测试设计不存在')
    return design


@router.put('/{design_id}', response_model=TestDesignResponse)
def update_testdesign(design_id: int, data: TestDesignCreate, db: Session = Depends(get_db)):
    design = db.get(TestDesign, design_id)
    if not design:
        raise HTTPException(404, '测试设计不存在')
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(design, k, v)
    db.commit()
    db.refresh(design)
    return design


@router.delete('/{design_id}', status_code=204)
def delete_testdesign(design_id: int, db: Session = Depends(get_db)):
    design = db.get(TestDesign, design_id)
    if not design:
        raise HTTPException(404, '测试设计不存在')
    db.delete(design)
    db.commit()


@router.post('/{design_id}/generate')
def generate_design(design_id: int, db: Session = Depends(get_db)):
    """Generate test design (sync fallback for non-WebSocket clients)."""
    design = db.get(TestDesign, design_id)
    if not design:
        raise HTTPException(404, '测试设计不存在')
    from services.testdesign_service import generate_test_design_sync
    full_md = generate_test_design_sync(design)
    return {'full_md': full_md, 'status': design.status}


@router.post('/{design_id}/refine')
def refine_design(design_id: int, req: RefineRequest, db: Session = Depends(get_db)):
    """Refine test design based on review feedback (sync fallback)."""
    design = db.get(TestDesign, design_id)
    if not design:
        raise HTTPException(404, '测试设计不存在')
    from services.testdesign_service import refine_test_design_sync
    full_md = refine_test_design_sync(design, req)
    return {'full_md': full_md, 'status': design.status}


@router.post('/{design_id}/reviews')
def update_reviews(design_id: int, reviews: list[ReviewItem], db: Session = Depends(get_db)):
    """Batch update review items for a test design."""
    design = db.get(TestDesign, design_id)
    if not design:
        raise HTTPException(404, '测试设计不存在')
    updated_count = 0
    for item in reviews:
        existing = (
            db.query(DesignReview)
            .filter_by(test_design_id=design_id, node_path=item.node_path)
            .first()
        )
        if existing:
            existing.node_text = item.node_text
            existing.status = item.status
            existing.feedback = item.feedback
            updated_count += 1
        else:
            review = DesignReview(
                test_design_id=design_id,
                node_path=item.node_path,
                node_text=item.node_text,
                status=item.status,
                feedback=item.feedback,
            )
            db.add(review)
            updated_count += 1
    db.commit()
    return {'updated_count': updated_count}


@router.post('/{design_id}/approve')
def approve_design(design_id: int, db: Session = Depends(get_db)):
    """Approve a test design."""
    design = db.get(TestDesign, design_id)
    if not design:
        raise HTTPException(404, '测试设计不存在')
    design.status = 'approved'
    db.commit()
    db.refresh(design)
    return {'status': design.status}


@router.post('/{design_id}/revert-review')
def revert_to_review(design_id: int, db: Session = Depends(get_db)):
    """Revert test design status back to reviewing."""
    design = db.get(TestDesign, design_id)
    if not design:
        raise HTTPException(404, '测试设计不存在')
    design.status = 'reviewing'
    db.commit()
    db.refresh(design)
    return {'status': design.status}


@router.post('/{design_id}/sync-kb')
def sync_to_kb(design_id: int, req: SyncKBRequest, db: Session = Depends(get_db)):
    """Sync approved test design to knowledge base."""
    design = db.get(TestDesign, design_id)
    if not design:
        raise HTTPException(404, '测试设计不存在')
    from services.knowledge_sync import embed_approved_design, embed_test_cases_from_parsed, embed_test_cases
    dc, tc = 0, 0
    if req.mode == 'A':
        dc, tc = embed_approved_design(design)
    elif req.mode == 'B':
        embed_test_cases(design)
        dc, tc = 0, 0
    elif req.mode == 'C':
        # Mode C: embed test cases parsed from full_md (same as mode A but without design doc)
        dc, tc = embed_test_cases_from_parsed(design)
    design.status = 'approved'
    db.commit()
    return {'design_chunks': dc, 'testcase_count': tc}


@router.post('/{design_id}/preview-xlsx')
async def preview_xlsx(design_id: int, db: Session = Depends(get_db)):
    """Preview xlsx content without saving."""
    design = db.get(TestDesign, design_id)
    if not design:
        raise HTTPException(404, '测试设计不存在')
    from parsers.md_parser import extract_step2, parse_step2_to_cases
    from parsers.xlsx_generator import generate_xlsx

    step2_text = extract_step2(design.full_md)
    product = design.project.product if design.project else ''
    cases = parse_step2_to_cases(step2_text, product)
    if not cases:
        raise HTTPException(400, '未找到测试用例数据')

    xlsx_bytes = generate_xlsx(cases, product)
    from fastapi.responses import Response
    return Response(
        content=xlsx_bytes,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=preview.xlsx'},
    )
