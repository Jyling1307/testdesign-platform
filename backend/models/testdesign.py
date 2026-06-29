from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class TestDesign(Base):
    __tablename__ = 'testdesigns_testdesign'

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects_project.id'))
    document_id: Mapped[int] = mapped_column(ForeignKey('documents_document.id'))
    version: Mapped[int] = mapped_column(Integer, default=1)
    full_md: Mapped[str] = mapped_column(Text, default='')
    xlsx_file_path: Mapped[str | None] = mapped_column('xlsx_file', String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='draft')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    project: Mapped['Project'] = relationship(back_populates='testdesigns')
    document: Mapped['Document'] = relationship(back_populates='testdesigns')
    reviews: Mapped[list['DesignReview']] = relationship(back_populates='test_design', cascade='all, delete-orphan')
    testcases: Mapped[list['TestCase']] = relationship(back_populates='test_design', cascade='all, delete-orphan')


class DesignReview(Base):
    __tablename__ = 'testdesigns_designreview'
    __table_args__ = (UniqueConstraint('test_design_id', 'node_path'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    test_design_id: Mapped[int] = mapped_column(ForeignKey('testdesigns_testdesign.id'))
    node_path: Mapped[str] = mapped_column(String(1000))
    node_text: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(10), default='pending')
    feedback: Mapped[str] = mapped_column(Text, default='')

    test_design: Mapped['TestDesign'] = relationship(back_populates='reviews')
