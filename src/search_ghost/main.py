"""
FastAPI application entry point.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from search_ghost.api import chat, documents, search, tasks
from search_ghost.config import get_settings
from search_ghost.kb import KnowledgeBase
from search_ghost.layers.ingestion.router import router as ingest_router
from search_ghost.worker.worker import BackgroundWorker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    kb = KnowledgeBase(settings)
    await kb.initialize()

    worker = BackgroundWorker(kb, concurrency=settings.worker_concurrency)
    worker.start()

    app.state.kb = kb
    app.state.worker = worker

    logger.info("search-ghost started — KB at %s", settings.kb_path)
    yield

    await worker.stop()
    await kb.close()
    logger.info("search-ghost stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="search-ghost",
        description="Local-first personal knowledge base with hybrid search and RAG chat",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routers
    app.include_router(ingest_router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(chat.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(tasks.router, prefix="/api")

    # Serve frontend static files in production
    static_dir = Path(__file__).parent.parent.parent / "web" / "dist"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
