from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from deps import get_db
from models.testcase import TestCase
from schemas.testcase import TestCaseResponse, TestCaseCreate

router = APIRouter(prefix='/api/testcases', tags=['testcases'])


@router.get('/', response_model=list[TestCaseResponse])
def list_testcases(test_design_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(TestCase)
    if test_design_id:
        q = q.filter(TestCase.test_design_id == test_design_id)
    return q.all()


@router.post('/', response_model=TestCaseResponse, status_code=201)
def create_testcase(data: TestCaseCreate, db: Session = Depends(get_db)):
    tc = TestCase(**data.model_dump())
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return tc


@router.get('/{tc_id}', response_model=TestCaseResponse)
def get_testcase(tc_id: int, db: Session = Depends(get_db)):
    tc = db.get(TestCase, tc_id)
    if not tc:
        raise HTTPException(404, '用例不存在')
    return tc


@router.put('/{tc_id}', response_model=TestCaseResponse)
def update_testcase(tc_id: int, data: TestCaseCreate, db: Session = Depends(get_db)):
    tc = db.get(TestCase, tc_id)
    if not tc:
        raise HTTPException(404, '用例不存在')
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(tc, k, v)
    db.commit()
    db.refresh(tc)
    return tc


@router.delete('/{tc_id}', status_code=204)
def delete_testcase(tc_id: int, db: Session = Depends(get_db)):
    tc = db.get(TestCase, tc_id)
    if not tc:
        raise HTTPException(404, '用例不存在')
    db.delete(tc)
    db.commit()


@router.post('/{tc_id}/export-xlsx')
def export_xlsx(tc_id: int, db: Session = Depends(get_db)):
    """Export test design cases as xlsx. tc_id is actually TestDesign id."""
    from models.testdesign import TestDesign
    from parsers.md_parser import extract_step2, parse_step2_to_cases
    from parsers.xlsx_generator import generate_xlsx
    from config import MEDIA_DIR

    design = db.get(TestDesign, tc_id)
    if not design:
        raise HTTPException(404, '测试设计不存在')

    step2_text = extract_step2(design.full_md)
    product = design.project.product if design.project else ''
    cases = parse_step2_to_cases(step2_text, product)

    if not cases:
        raise HTTPException(400, '未找到测试用例数据')

    xlsx_bytes = generate_xlsx(cases, product)

    # Save to file
    xlsx_dir = MEDIA_DIR / 'xlsx'
    xlsx_dir.mkdir(parents=True, exist_ok=True)
    xlsx_path = xlsx_dir / f"design_{tc_id}.xlsx"
    with open(xlsx_path, 'wb') as f:
        f.write(xlsx_bytes)

    design.xlsx_file_path = str(xlsx_path)
    design.status = 'exported'
    db.commit()

    filename = f"测试用例_{design.document.title if design.document else tc_id}.xlsx"
    return FileResponse(
        path=str(xlsx_path),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        filename=filename,
    )
