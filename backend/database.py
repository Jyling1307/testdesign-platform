"""SQLAlchemy engine, session, and base."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import settings, DATA_DIR

engine = create_engine(
    f'sqlite:///{DATA_DIR / "db.sqlite3"}',
    connect_args={'check_same_thread': False},
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
