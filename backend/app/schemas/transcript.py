"""Transcript Pydantic Schemas"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TranscriptWord(BaseModel):
    word: str
    start: float
    end: float
    probability: Optional[float] = None


class TranscriptSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    words: Optional[List[TranscriptWord]] = None
    avg_logprob: Optional[float] = None
    no_speech_prob: Optional[float] = None


class TranscriptResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    video_id: str
    full_text: Optional[str] = None
    segments: Optional[List[Dict]] = None
    language: Optional[str] = None
    model_used: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
