from datetime import datetime

from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Project(Base):
    __tablename__ = 'projects_project'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    product: Mapped[str] = mapped_column(String(100), default='')
    description: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    documents: Mapped[list['Document']] = relationship(back_populates='project', cascade='all, delete-orphan')
    testdesigns: Mapped[list['TestDesign']] = relationship(back_populates='project', cascade='all, delete-orphan')
    knowledge: Mapped[list['KnowledgeEntry']] = relationship(back_populates='project', cascade='all, delete-orphan')
