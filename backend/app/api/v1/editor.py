"""
Editor API router — manages timeline, caption tracks, effects, and edits for clips.
GET   /api/v1/editor/{clip_id}
PUT   /api/v1/editor/{clip_id}
POST  /api/v1/editor/{clip_id}/reset
"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.logging_config import get_logger
from app.core.security import get_current_user
from app.models.clip import Clip
from app.models.editing_project import EditingProject
from app.models.project import Project
from app.models.user import User
from app.schemas.editing_project import (
    CaptionItem,
    CaptionWordHighlight,
    EditingProjectResponse,
    EditingProjectUpdate,
    TimelineData,
    TimelineTrackItem,
    VideoEffects,
    ExportSettings,
)

router = APIRouter()
logger = get_logger(__name__)


def _build_default_timeline(clip: Clip) -> dict:
    """Initialize a default timeline structure using the clip's duration and segments."""
    duration = clip.duration or (clip.end_time - clip.start_time)
    
    # 1. Base video track
    tracks = [
        TimelineTrackItem(
            id=str(uuid.uuid4()),
            track_type="video",
            start_time=0.0,
            end_time=duration,
            source_start=clip.start_time,
            source_end=clip.end_time,
            volume=1.0,
            opacity=1.0,
            z_index=1,
        ).model_dump()
    ]

    # 2. Extract captions from clip segments
    captions = []
    if clip.segments:
        for idx, seg in enumerate(clip.segments):
            seg_start = max(0.0, float(seg.get("start", 0.0)) - clip.start_time)
            seg_end = max(0.0, float(seg.get("end", 0.0)) - clip.start_time)
            if seg_end <= seg_start:
                continue

            words = []
            for w in seg.get("words", []):
                w_start = max(0.0, float(w.get("start", 0.0)) - clip.start_time)
                w_end = max(0.0, float(w.get("end", 0.0)) - clip.start_time)
                words.append(
                    CaptionWordHighlight(
                        word=w.get("word", ""),
                        start=w_start,
                        end=w_end,
                        color="#FFD700",
                    )
                )

            captions.append(
                CaptionItem(
                    id=str(uuid.uuid4()),
                    start_time=round(seg_start, 3),
                    end_time=round(seg_end, 3),
                    text=seg.get("text", "").strip(),
                    font_family="Inter",
                    font_size=28,
                    font_color="#FFFFFF",
                    position="bottom",
                    animation_preset="word_highlight" if words else "fade",
                    words=words if words else None,
                ).model_dump()
            )

    timeline = TimelineData(
        total_duration=duration,
        aspect_ratio="9:16",
        tracks=tracks,
        captions=captions,
        effects=VideoEffects(),
    )
    return timeline.model_dump()


@router.get(
    "/{clip_id}",
    response_model=EditingProjectResponse,
    summary="Get or initialize editing project for a clip",
)
async def get_or_create_editing_project(
    clip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clip = await _get_owned_clip(clip_id, current_user.id, db)

    # Check if editing project already exists
    result = await db.execute(
        select(EditingProject).where(EditingProject.clip_id == clip.id)
    )
    editing_project = result.scalar_one_or_none()

    if not editing_project:
        # Auto-initialize
        default_timeline = _build_default_timeline(clip)
        default_export = ExportSettings().model_dump()

        editing_project = EditingProject(
            clip_id=clip.id,
            timeline_data=default_timeline,
            export_settings=default_export,
            version=1,
        )
        db.add(editing_project)
        await db.commit()
        await db.refresh(editing_project)
        logger.info("Initialized default editing project", clip_id=clip.id)

    return editing_project


@router.put(
    "/{clip_id}",
    response_model=EditingProjectResponse,
    summary="Update timeline data and export settings",
)
async def update_editing_project(
    clip_id: str,
    payload: EditingProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clip = await _get_owned_clip(clip_id, current_user.id, db)

    result = await db.execute(
        select(EditingProject).where(EditingProject.clip_id == clip.id)
    )
    editing_project = result.scalar_one_or_none()
    if not editing_project:
        # Create it if it doesn't exist
        default_timeline = _build_default_timeline(clip)
        editing_project = EditingProject(
            clip_id=clip.id,
            timeline_data=payload.timeline_data.model_dump() if payload.timeline_data else default_timeline,
            export_settings=payload.export_settings.model_dump() if payload.export_settings else ExportSettings().model_dump(),
            version=1,
        )
        db.add(editing_project)
    else:
        if payload.timeline_data is not None:
            editing_project.timeline_data = payload.timeline_data.model_dump()
        if payload.export_settings is not None:
            editing_project.export_settings = payload.export_settings.model_dump()
        editing_project.version += 1

    await db.commit()
    await db.refresh(editing_project)
    logger.info("Updated editing project", clip_id=clip.id, version=editing_project.version)
    return editing_project


@router.post(
    "/{clip_id}/reset",
    response_model=EditingProjectResponse,
    summary="Reset timeline and effects back to defaults",
)
async def reset_editing_project(
    clip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clip = await _get_owned_clip(clip_id, current_user.id, db)

    result = await db.execute(
        select(EditingProject).where(EditingProject.clip_id == clip.id)
    )
    editing_project = result.scalar_one_or_none()

    default_timeline = _build_default_timeline(clip)
    default_export = ExportSettings().model_dump()

    if not editing_project:
        editing_project = EditingProject(
            clip_id=clip.id,
            timeline_data=default_timeline,
            export_settings=default_export,
            version=1,
        )
        db.add(editing_project)
    else:
        editing_project.timeline_data = default_timeline
        editing_project.export_settings = default_export
        editing_project.version += 1

    await db.commit()
    await db.refresh(editing_project)
    return editing_project


# ── Helper ───────────────────────────────────────────────────────────────────
async def _get_owned_clip(clip_id: str, user_id: str, db: AsyncSession) -> Clip:
    result = await db.execute(
        select(Clip)
        .join(Project, Clip.project_id == Project.id)
        .where(Clip.id == clip_id, Project.user_id == user_id)
    )
    clip: Clip | None = result.scalar_one_or_none()
    if not clip:
        raise NotFoundError("Clip", clip_id)
    return clip
