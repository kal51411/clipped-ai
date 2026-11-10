"""
Storage Service — abstraction over local filesystem and S3-compatible storage.
Swappable via STORAGE_BACKEND env var: "local" | "s3"
"""
from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.exceptions import StorageError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class StorageService(ABC):
    """Base interface for storage backends."""

    @abstractmethod
    async def upload(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        """Upload bytes and return the storage path/key."""
        ...

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download and return bytes for the given key."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete an object by key."""
        ...

    @abstractmethod
    def get_public_url(self, key: str) -> Optional[str]:
        """Return a public URL for the key, or None if not applicable."""
        ...


class LocalStorage(StorageService):
    """Development: stores files on local filesystem."""

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        dest = self.base_path / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        logger.debug("LocalStorage upload", key=key, bytes=len(data))
        return str(dest)

    async def download(self, key: str) -> bytes:
        # key may be an absolute path or relative
        path = Path(key) if os.path.isabs(key) else self.base_path / key
        if not path.exists():
            raise StorageError(f"File not found: {key}")
        return path.read_bytes()

    async def delete(self, key: str) -> None:
        path = Path(key) if os.path.isabs(key) else self.base_path / key
        if path.exists():
            path.unlink()
            logger.debug("LocalStorage delete", key=key)

    def get_public_url(self, key: str) -> Optional[str]:
        # In dev, serve files via FastAPI static mount or direct path
        return None


class S3Storage(StorageService):
    """Production: Cloudflare R2 / AWS S3 compatible storage."""

    def __init__(self):
        if not all([
            settings.S3_ENDPOINT_URL,
            settings.S3_ACCESS_KEY_ID,
            settings.S3_SECRET_ACCESS_KEY,
            settings.S3_BUCKET_NAME,
        ]):
            raise StorageError(
                "S3 storage requires S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, "
                "S3_SECRET_ACCESS_KEY, and S3_BUCKET_NAME environment variables"
            )

        import boto3
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
        )
        self._bucket = settings.S3_BUCKET_NAME

    async def upload(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        try:
            import io
            self._client.upload_fileobj(
                io.BytesIO(data),
                self._bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
            logger.info("S3 upload", bucket=self._bucket, key=key, bytes=len(data))
            return key
        except Exception as e:
            raise StorageError(f"S3 upload failed for key '{key}': {e}") from e

    async def download(self, key: str) -> bytes:
        try:
            import io
            buf = io.BytesIO()
            self._client.download_fileobj(self._bucket, key, buf)
            return buf.getvalue()
        except Exception as e:
            raise StorageError(f"S3 download failed for key '{key}': {e}") from e

    async def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception as e:
            raise StorageError(f"S3 delete failed for key '{key}': {e}") from e

    def get_public_url(self, key: str) -> Optional[str]:
        if settings.S3_PUBLIC_URL_BASE:
            return f"{settings.S3_PUBLIC_URL_BASE.rstrip('/')}/{key}"
        return None


# ── Singleton factory ─────────────────────────────────────────────────────────
_storage_instance: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create the global storage service instance."""
    global _storage_instance
    if _storage_instance is None:
        backend = settings.STORAGE_BACKEND.lower()
        if backend == "s3":
            _storage_instance = S3Storage()
        else:
            _storage_instance = LocalStorage()
        logger.info("Storage service initialized", backend=backend)
    return _storage_instance
