"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings, DATA_DIR, MEDIA_DIR
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


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
