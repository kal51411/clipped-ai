"""
Clipped-AI Backend — Application Entry Point
FastAPI app factory with CORS, middleware, routers, and lifespan events.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, Base
from app.core.exceptions import ClippedAIException, register_exception_handlers
from app.core.logging_config import setup_logging, get_logger

# ── Import all models so SQLAlchemy discovers them ──────────────────────────
import app.models  # noqa: F401

from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

# ── Versioned API routers ────────────────────────────────────────────────────
from app.api.v1 import health, auth, videos, projects, clips, jobs, editor

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle."""
    setup_logging()
    logger.info("Starting Clipped-AI backend", version=settings.APP_VERSION)

    # Ensure storage and output directories exist
    Path(settings.LOCAL_STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # Create all tables (dev mode — use Alembic in production)
    if settings.AUTO_CREATE_TABLES:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured")

    logger.info("Application ready", environment=settings.ENVIRONMENT)
    yield

    logger.info("Shutting down Clipped-AI backend")


def create_application() -> FastAPI:
    app = FastAPI(
        title="Clipped-AI API",
        description="AI-powered short-form video generation SaaS",
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.SHOW_DOCS else None,
        redoc_url="/redoc" if settings.SHOW_DOCS else None,
        openapi_url="/openapi.json" if settings.SHOW_DOCS else None,
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request timing middleware ─────────────────────────────────────────────
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        return response

    # ── Exception handlers ───────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Static Media Mounting for local video previews ───────────────────────
    os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    app.mount("/media/storage", StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="storage")
    app.mount("/media/output", StaticFiles(directory=settings.OUTPUT_DIR), name="output")

    # ── API routes ───────────────────────────────────────────────────────────
    PREFIX = "/api/v1"
    app.include_router(health.router, prefix=PREFIX, tags=["Health"])
    app.include_router(auth.router, prefix=f"{PREFIX}/auth", tags=["Auth"])
    app.include_router(videos.router, prefix=f"{PREFIX}/videos", tags=["Videos"])
    app.include_router(projects.router, prefix=f"{PREFIX}/projects", tags=["Projects"])
    app.include_router(clips.router, prefix=f"{PREFIX}/clips", tags=["Clips"])
    app.include_router(jobs.router, prefix=f"{PREFIX}/jobs", tags=["Jobs"])
    app.include_router(editor.router, prefix=f"{PREFIX}/editor", tags=["Editor"])

    return app


app = create_application()
