"""Project Pydantic Schemas"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    prompt: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    status: str
    prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
    page: int
    page_size: int


class QuickYoutubeRequest(BaseModel):
    url: str = Field(..., description="YouTube or online video URL")
    title: Optional[str] = Field(default=None, max_length=255)
    prompt: Optional[str] = Field(
        default="Find the most interesting, viral, and engaging moments for short-form clips",
        max_length=5000,
    )
    target_duration_seconds: Optional[int] = Field(default=30, ge=10, le=120)
    num_candidates: Optional[int] = Field(default=5, ge=1, le=10)


class QuickYoutubeResponse(BaseModel):
    project: ProjectResponse
    video_id: str
    job_id: str
    message: str

