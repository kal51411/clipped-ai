"""Editing Project and Timeline Pydantic Schemas"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CaptionWordHighlight(BaseModel):
    word: str
    start: float
    end: float
    color: Optional[str] = "#FFD700"  # Gold highlight


class CaptionItem(BaseModel):
    id: str
    start_time: float
    end_time: float
    text: str
    font_family: str = "Inter"
    font_size: int = 28
    font_color: str = "#FFFFFF"
    background_color: Optional[str] = None
    position: str = "bottom"  # top, center, bottom
    animation_preset: str = "fade"  # none, fade, pop, word_highlight, bounce
    words: Optional[List[CaptionWordHighlight]] = None


class TimelineTrackItem(BaseModel):
    id: str
    track_type: str = "video"  # video, caption, audio, overlay
    start_time: float
    end_time: float
    source_start: float = 0.0
    source_end: float = 0.0
    volume: float = 1.0
    opacity: float = 1.0
    z_index: int = 1


class VideoEffects(BaseModel):
    zoom_level: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    brightness: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0
    filter_preset: str = "normal"  # normal, cinematic, vibrant, warm, cool, b&w
    transition_in: str = "fade"    # none, fade, zoom_in, slide_left
    transition_out: str = "none"


class TimelineData(BaseModel):
    total_duration: float
    aspect_ratio: str = "9:16"  # 9:16, 16:9, 1:1
    tracks: List[TimelineTrackItem] = Field(default_factory=list)
    captions: List[CaptionItem] = Field(default_factory=list)
    effects: VideoEffects = Field(default_factory=VideoEffects)


class ExportSettings(BaseModel):
    resolution: str = "1080x1920"
    fps: int = 30
    video_bitrate_kbps: int = 4500
    audio_bitrate_kbps: int = 128
    format: str = "mp4"
    include_captions: bool = True
    burn_subtitles: bool = True


class EditingProjectCreate(BaseModel):
    clip_id: str
    timeline_data: Optional[TimelineData] = None
    export_settings: Optional[ExportSettings] = None


class EditingProjectUpdate(BaseModel):
    timeline_data: Optional[TimelineData] = None
    export_settings: Optional[ExportSettings] = None
    version: Optional[int] = None


class EditingProjectResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    clip_id: str
    timeline_data: Optional[Dict[str, Any]] = None
    export_settings: Optional[Dict[str, Any]] = None
    version: int
    created_at: datetime
    updated_at: datetime
