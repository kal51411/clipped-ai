"""
Videos router
POST /api/v1/videos/upload          — upload a video file
GET  /api/v1/videos/{video_id}      — get video details
GET  /api/v1/videos/{video_id}/transcript — get video transcript
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import (
    FileTooLargeError,
    ForbiddenError,
    NotFoundError,
    UnsupportedFormatError,
    ValidationError,
)
from app.core.logging_config import get_logger
from app.core.security import get_current_user
from app.models.project import Project
from app.models.transcript import Transcript
from app.models.user import User
from app.models.video import Video
from app.schemas.transcript import TranscriptResponse
from app.schemas.video import VideoResponse, VideoUrlImportRequest

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/upload",
    response_model=VideoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a video file to a project",
)
async def upload_video(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project: Project | None = proj_result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", project_id)
    if project.user_id != current_user.id:
        raise ForbiddenError("You do not own this project")

    # Validate file extension
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in settings.SUPPORTED_VIDEO_FORMATS:
        raise UnsupportedFormatError(ext, settings.SUPPORTED_VIDEO_FORMATS)

    # Read and size-check
    content = await file.read()
    file_size = len(content)
    if file_size > settings.max_upload_size_bytes:
        raise FileTooLargeError(settings.MAX_UPLOAD_SIZE_MB)

    if file_size == 0:
        raise ValidationError("Uploaded file is empty")

    # Determine storage path
    video_id = str(uuid.uuid4())
    safe_name = f"{video_id}.{ext}"

    if settings.STORAGE_BACKEND == "local":
        storage_root = Path(settings.LOCAL_STORAGE_PATH) / "videos"
        storage_root.mkdir(parents=True, exist_ok=True)
        storage_path = str(storage_root / safe_name)
        with open(storage_path, "wb") as f:
            f.write(content)
    else:
        # S3 upload — imported lazily to avoid import errors when not configured
        from app.integrations.storage import get_storage_service
        svc = get_storage_service()
        storage_path = await svc.upload(
            data=content,
            key=f"videos/{safe_name}",
            content_type=file.content_type or "video/mp4",
        )

    # Persist video record (metadata extracted by background job)
    video = Video(
        id=video_id,
        project_id=project_id,
        original_filename=filename,
        storage_path=storage_path,
        storage_backend=settings.STORAGE_BACKEND,
        file_size_bytes=file_size,
        mime_type=file.content_type,
        status="uploaded",
    )
    db.add(video)

    # Kick off background metadata extraction + transcription
    try:
        from app.workers.tasks import process_video_task
        task = process_video_task.delay(video_id=video_id, project_id=project_id)
        logger.info("Queued process_video_task", video_id=video_id, task_id=task.id)
    except Exception as e:
        logger.warning(
            "Could not enqueue process_video_task via Celery, running in background task",
            error=str(e),
        )
        background_tasks.add_task(
            process_video_task.apply,
            kwargs={"video_id": video_id, "project_id": project_id},
        )

    await db.commit()
    await db.refresh(video)
    logger.info(
        "Video uploaded",
        video_id=video_id,
        filename=filename,
        size_bytes=file_size,
    )
    return video


@router.post(
    "/import-url",
    response_model=VideoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import video from YouTube or public video URL",
)
async def import_video_url(
    payload: VideoUrlImportRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import asyncio
    from app.video.ingestion.url_downloader import download_video_from_url

    # Validate project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == payload.project_id)
    )
    project: Project | None = proj_result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", payload.project_id)
    if project.user_id != current_user.id:
        raise ForbiddenError("You do not own this project")

    video_id = str(uuid.uuid4())
    safe_name = f"{video_id}.mp4"
    storage_root = Path(settings.LOCAL_STORAGE_PATH) / "videos"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_path = str(storage_root / safe_name)

    # Download in background thread to keep event loop responsive
    info = await asyncio.to_thread(download_video_from_url, payload.url, storage_path)

    title = info.get("title") or f"Imported Video ({video_id[:8]})"
    filename = f"{title}.mp4"
    file_size = info.get("file_size_bytes", 0)

    video = Video(
        id=video_id,
        project_id=payload.project_id,
        original_filename=filename,
        storage_path=storage_path,
        storage_backend="local",
        file_size_bytes=file_size,
        mime_type="video/mp4",
        status="uploaded",
    )
    db.add(video)

    # Kick off background metadata extraction + transcription
    try:
        from app.workers.tasks import process_video_task
        task = process_video_task.delay(video_id=video_id, project_id=payload.project_id)
        logger.info("Queued process_video_task for imported URL", video_id=video_id, task_id=task.id)
    except Exception as e:
        logger.warning(
            "Could not enqueue process_video_task via Celery, running in background task",
            error=str(e),
        )
        background_tasks.add_task(
            process_video_task.apply,
            kwargs={"video_id": video_id, "project_id": payload.project_id},
        )

    await db.commit()
    await db.refresh(video)
    return video


@router.get(
    "/{video_id}",
    response_model=VideoResponse,
    summary="Get video details",
)
async def get_video(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video = await _get_owned_video(video_id, current_user.id, db)
    return video


@router.get(
    "/{video_id}/transcript",
    response_model=TranscriptResponse,
    summary="Get transcript for a video",
)
async def get_transcript(
    video_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    video = await _get_owned_video(video_id, current_user.id, db)
    result = await db.execute(
        select(Transcript).where(Transcript.video_id == video.id)
    )
    transcript: Transcript | None = result.scalar_one_or_none()
    if not transcript:
        raise NotFoundError("Transcript for video", video_id)
    return transcript


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _get_owned_video(
    video_id: str, user_id: str, db: AsyncSession
) -> Video:
    result = await db.execute(
        select(Video)
        .join(Project, Video.project_id == Project.id)
        .where(Video.id == video_id, Project.user_id == user_id)
    )
    video: Video | None = result.scalar_one_or_none()
    if not video:
        raise NotFoundError("Video", video_id)
    return video
