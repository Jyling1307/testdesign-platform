"""Application configuration loaded from .env."""

from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
MEDIA_DIR = DATA_DIR / 'media'


class Settings(BaseSettings):
    # Django compat
    SECRET_KEY: str = 'change-me-to-a-random-secret-key'
    DEBUG: bool = True
    ALLOWED_HOSTS: str = '*'

    # LLM (Anthropic-compatible, ZhipuAI GLM)
    LLM_BASE_URL: str = 'https://open.bigmodel.cn/api/anthropic'
    LLM_API_KEY: str = ''
    LLM_MODEL: str = 'glm-5-turbo'

    # Embedding (SiliconFlow bge-m3)
    EMBEDDING_BASE_URL: str = 'https://api.siliconflow.cn/v1/'
    EMBEDDING_API_KEY: str = ''
    EMBEDDING_MODEL: str = 'BAAI/bge-m3'

    # Rerank (SiliconFlow bge-reranker-v2-m3)
    RERANK_ENABLED: bool = False
    RERANK_MODEL: str = 'BAAI/bge-reranker-v2-m3'
    RERANK_TOP_N: int = 5

    # Text Chunking (Dify parent-child mode)
    PARENT_CHUNK_SIZE: int = 4000
    PARENT_CHUNK_OVERLAP: int = 400
    CHILD_CHUNK_SIZE: int = 800
    CHILD_CHUNK_OVERLAP: int = 100

    # ChromaDB
    CHROMA_PERSIST_DIR: str = str(DATA_DIR / 'chroma_db')

    # Knowledge Base
    KB_WATCH_DIR: str = ''

    # CORS
    CORS_ORIGINS: list[str] = ['http://localhost:5173', 'http://127.0.0.1:5173']

    model_config = {
        'env_file': str(BASE_DIR / '.env'),
        'env_file_encoding': 'utf-8',
        'extra': 'ignore',
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
