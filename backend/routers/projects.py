from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from deps import get_db
from models.project import Project
from schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter(prefix='/api/projects', tags=['projects'])


@router.get('/', response_model=list[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.post('/', response_model=ProjectResponse, status_code=201)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get('/{project_id}', response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, '项目不存在')
    return project


@router.put('/{project_id}', response_model=ProjectResponse)
def update_project(project_id: int, data: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, '项目不存在')
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(project, k, v)
    db.commit()
    db.refresh(project)
    return project


@router.delete('/{project_id}', status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, '项目不存在')
    db.delete(project)
    db.commit()
