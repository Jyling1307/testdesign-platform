"""FastAPI application entry point."""

# CentOS 7 兼容：chromadb 需要 SQLite >= 3.35.0，系统自带 3.7（旧）
# 检测 SQLite 版本，旧版用 pysqlite3 替换（必须在 import chromadb 之前）
try:
    import sqlite3 as _sqlite3_check
    if _sqlite3_check.sqlite_version_info < (3, 35, 0):
        import pysqlite3
        import sys
        sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass  # pysqlite3 未装（Windows 等新系统不需要）

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings, DATA_DIR, MEDIA_DIR, BASE_DIR
from database import engine, Base

# Import all models to register them with SQLAlchemy metadata
from models import *  # noqa: F401,F403

# Import routers
from routers.projects import router as projects_router
from routers.documents import router as documents_router
from routers.knowledge import router as knowledge_router
from routers.testdesigns import router as testdesigns_router
from routers.testcases import router as testcases_router

# Import WebSocket handlers
from websocket.testdesign_ws import websocket_generate, websocket_refine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化数据库表（首次启动自动建表，避免空 db.sqlite3）
    Base.metadata.create_all(bind=engine)
    # Ensure media directory exists
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    (MEDIA_DIR / 'documents').mkdir(exist_ok=True)
    (MEDIA_DIR / 'xlsx').mkdir(exist_ok=True)
    yield


app = FastAPI(
    title='TestDesignAI Platform',
    version='2.0.0',
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if not settings.DEBUG else ['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Register WebSocket routes FIRST, before routers and static mounts
@app.websocket('/ws/gen/{design_id}')
async def ws_generate(websocket: WebSocket, design_id: int):
    await websocket_generate(websocket, design_id)

@app.websocket('/ws/ref/{design_id}')
async def ws_refine(websocket: WebSocket, design_id: int):
    await websocket_refine(websocket, design_id)

# Static files (media uploads)
if MEDIA_DIR.exists():
    app.mount('/media', StaticFiles(directory=str(MEDIA_DIR)), name='media')

# Register routers
app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(knowledge_router)
app.include_router(testdesigns_router)
app.include_router(testcases_router)

# Serve frontend SPA (must be after all API routes; /api/* 会先匹配)
FRONTEND_DIST = BASE_DIR.parent / 'frontend-dist'
if FRONTEND_DIST.exists():
    from fastapi.responses import FileResponse

    # 静态资源目录（JS/CSS 高效服务）
    if (FRONTEND_DIST / 'assets').exists():
        app.mount('/assets', StaticFiles(directory=str(FRONTEND_DIST / 'assets')), name='assets')

    @app.get('{full_path:path}')
    async def spa_fallback(full_path: str):
        """SPA fallback：尝试返回实际文件，否则返回 index.html 让 Vue Router 处理。"""
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / 'index.html'))


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
