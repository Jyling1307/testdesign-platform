"""FastAPI dependency injection helpers."""

from functools import lru_cache
from database import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
