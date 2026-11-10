"""
Clipped-AI — Application Configuration
All settings read from environment variables with sane defaults.
"""
from __future__ import annotations

import os
from typing import List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Clipped-AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SHOW_DOCS: bool = True
    AUTO_CREATE_TABLES: bool = True

    # ── Server ───────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── CORS ─────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] | str = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: list[str] | str) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./clipped_ai.db"
    # For production: postgresql+asyncpg://user:password@host/dbname
    DATABASE_SYNC_URL: str = "sqlite:///./clipped_ai.db"
    # For production Alembic: postgresql://user:password@host/dbname

    # ── Authentication ───────────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_use_openssl_rand_hex_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24          # 24h
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Google OAuth ──────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/callback/google"

    # ── Gemini AI ────────────────────────────────────────────────────────────
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_ENABLED: bool = False  # auto-set by validator

    @model_validator(mode="after")
    def set_gemini_enabled(self) -> "Settings":
        self.GEMINI_ENABLED = bool(self.GEMINI_API_KEY)
        return self

    # ── Whisper Transcription ─────────────────────────────────────────────────
    WHISPER_MODEL_SIZE: str = "base"   # tiny | base | small | medium | large
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"  # int8 is fastest on CPU

    # ── Storage ───────────────────────────────────────────────────────────────
    STORAGE_BACKEND: str = "local"     # local | s3
    LOCAL_STORAGE_PATH: str = "./storage"
    # S3 / Cloudflare R2:
    S3_ENDPOINT_URL: Optional[str] = None
    S3_ACCESS_KEY_ID: Optional[str] = None
    S3_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None
    S3_REGION: str = "auto"
    S3_PUBLIC_URL_BASE: Optional[str] = None

    # ── Celery / Redis ─────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ── Video Processing ───────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 2048          # 2 GB
    SUPPORTED_VIDEO_FORMATS: List[str] = ["mp4", "mov", "avi", "mkv", "webm", "m4v"]
    TEMP_DIR: str = "/tmp/clipped_ai"
    OUTPUT_DIR: str = "./output"
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    # ── Clip Generation ────────────────────────────────────────────────────────
    DEFAULT_CLIP_DURATION_SECONDS: int = 60
    MIN_CLIP_DURATION_SECONDS: int = 10
    MAX_CLIP_DURATION_SECONDS: int = 180
    MAX_CANDIDATES_TO_SCORE: int = 20
    TOP_CANDIDATES_RETURNED: int = 5

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


# Singleton settings instance
settings = Settings()
