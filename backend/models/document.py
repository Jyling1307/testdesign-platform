from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Document(Base):
    __tablename__ = 'documents_document'

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects_project.id'))
    title: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column('file', String(500), default='')
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    file_type: Mapped[str] = mapped_column(String(10), default='')
    raw_text: Mapped[str] = mapped_column(Text, default='')
    parsed_structure: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default='uploaded')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    project: Mapped['Project'] = relationship(back_populates='documents')
    testdesigns: Mapped[list['TestDesign']] = relationship(back_populates='document', cascade='all, delete-orphan')
