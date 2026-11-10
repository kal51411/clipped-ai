"""Clip Pydantic Schemas"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GenerateClipsRequest(BaseModel):
    project_id: str
    prompt: str = Field(min_length=5, max_length=5000)
    target_duration_seconds: Optional[int] = Field(
        default=60, ge=10, le=180
    )
    num_candidates: Optional[int] = Field(default=5, ge=1, le=10)


class ClipUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=512)
    is_selected: Optional[bool] = None
    render_settings: Optional[Dict[str, Any]] = None


class ExportClipRequest(BaseModel):
    format: str = Field(default="mp4", pattern="^(mp4|webm)$")
    quality: str = Field(default="high", pattern="^(low|medium|high)$")
    include_captions: bool = True
    caption_style: Optional[Dict[str, Any]] = None


class ClipScoreBreakdown(BaseModel):
    relevance: float
    hook_strength: float
    context_completeness: float
    engagement_potential: float
    speech_clarity: float
    natural_boundaries: float


class ClipResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    start_time: float
    end_time: float
    duration: float
    title: Optional[str] = None
    transcript_text: Optional[str] = None
    score: float
    score_breakdown: Optional[Dict[str, Any]] = None
    rank: int
    status: str
    is_selected: bool
    storage_path: Optional[str] = None
    public_url: Optional[str] = None
    thumbnail_path: Optional[str] = None
    render_settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ClipListResponse(BaseModel):
    items: List[ClipResponse]
    total: int
