"""Video Pydantic Schemas"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class VideoMetadata(BaseModel):
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    has_audio: bool = True
    bitrate_kbps: Optional[int] = None
    file_size_bytes: Optional[int] = None


class VideoUrlImportRequest(BaseModel):
    project_id: str
    url: str


class VideoResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    original_filename: str
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    has_audio: bool
    bitrate_kbps: Optional[int] = None
    status: str
    storage_backend: str
    created_at: datetime
    updated_at: datetime
