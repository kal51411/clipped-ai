"""
Health check router — /api/v1/health, /api/v1/info, /api/v1/ready
"""
from __future__ import annotations

import os
import platform
import sys
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

router = APIRouter()

_start_time = datetime.now(timezone.utc)


@router.get("/health", summary="Health check")
async def health_check():
    return {
        "success": True,
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": (datetime.now(timezone.utc) - _start_time).total_seconds(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/ready", summary="Readiness check (includes DB ping)")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    checks: dict = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Gemini check
    checks["gemini_configured"] = settings.GEMINI_ENABLED

    # FFmpeg check
    ffmpeg_ok = os.path.exists(settings.FFMPEG_PATH) or _which(settings.FFMPEG_PATH)
    checks["ffmpeg"] = "ok" if ffmpeg_ok else "not found"

    all_ok = checks["database"] == "ok"
    return {
        "success": all_ok,
        "status": "ready" if all_ok else "degraded",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/info", summary="Application info")
async def app_info():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "python_version": sys.version.split()[0],
        "platform": platform.system(),
        "features": {
            "gemini_ai": settings.GEMINI_ENABLED,
            "whisper_model": settings.WHISPER_MODEL_SIZE,
            "storage_backend": settings.STORAGE_BACKEND,
            "max_upload_mb": settings.MAX_UPLOAD_SIZE_MB,
        },
    }


def _which(cmd: str) -> bool:
    import shutil
    return shutil.which(cmd) is not None
