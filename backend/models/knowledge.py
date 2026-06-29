from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class KnowledgeEntry(Base):
    __tablename__ = 'knowledge_knowledgeentry'

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey('projects_project.id'), nullable=True)
    source_type: Mapped[str] = mapped_column(String(20))
    source_id: Mapped[int] = mapped_column(Integer, default=0)
    chunk_text: Mapped[str] = mapped_column(Text, default='')
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    vector_id: Mapped[str] = mapped_column(String(200), unique=True)
    metadata_: Mapped[dict] = mapped_column('metadata', JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    project: Mapped['Project | None'] = relationship(back_populates='knowledge')
