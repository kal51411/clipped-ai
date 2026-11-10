"""
Clips router
POST  /api/v1/clips/generate         — kick off clip generation
GET   /api/v1/clips?project_id=...   — list clips for a project
GET   /api/v1/clips/{clip_id}        — get a specific clip
PATCH /api/v1/clips/{clip_id}        — update (title, selected, settings)
POST  /api/v1/clips/{clip_id}/render — trigger render
POST  /api/v1/clips/{clip_id}/export — export final MP4
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.core.logging_config import get_logger
from app.core.security import get_current_user
from app.models.clip import Clip
from app.models.job import Job
from app.models.project import Project
from app.models.user import User
from app.schemas.clip import (
    ClipListResponse,
    ClipResponse,
    ClipUpdate,
    ExportClipRequest,
    GenerateClipsRequest,
)
from app.schemas.job import JobResponse

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/generate",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start clip generation for a project (async job)",
)
async def generate_clips(
    payload: GenerateClipsRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify project ownership
    project = await _get_owned_project(payload.project_id, current_user.id, db)

    # Store the prompt on the project
    project.prompt = payload.prompt
    project.status = "processing"

    # Create a job record
    job = Job(
        project_id=project.id,
        job_type="clip_generation",
        status="pending",
        input_data={
            "prompt": payload.prompt,
            "target_duration_seconds": payload.target_duration_seconds,
            "num_candidates": payload.num_candidates,
        },
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Enqueue Celery task
    try:
        from app.workers.tasks import generate_clips_task
        task = generate_clips_task.delay(
            job_id=job.id,
            project_id=project.id,
            prompt=payload.prompt,
            target_duration=payload.target_duration_seconds,
            num_candidates=payload.num_candidates,
        )
        job.celery_task_id = task.id
        await db.commit()
        await db.refresh(job)
        logger.info("Enqueued generate_clips_task", job_id=job.id, task_id=task.id)
    except Exception as e:
        logger.warning(
            "Could not enqueue generate_clips_task via Celery, running in background task",
            error=str(e),
        )
        background_tasks.add_task(
            generate_clips_task.apply,
            kwargs={
                "job_id": job.id,
                "project_id": project.id,
                "prompt": payload.prompt,
                "target_duration": payload.target_duration_seconds,
                "num_candidates": payload.num_candidates,
            },
        )

    return job


@router.get(
    "",
    response_model=ClipListResponse,
    summary="List clips for a project",
)
async def list_clips(
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_project(project_id, current_user.id, db)

    result = await db.execute(
        select(Clip)
        .where(Clip.project_id == project_id)
        .order_by(Clip.rank.asc(), Clip.score.desc())
    )
    clips = result.scalars().all()
    return ClipListResponse(
        items=[ClipResponse.model_validate(c) for c in clips],
        total=len(clips),
    )


@router.get(
    "/{clip_id}",
    response_model=ClipResponse,
    summary="Get a specific clip",
)
async def get_clip(
    clip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clip = await _get_owned_clip(clip_id, current_user.id, db)
    return clip


@router.patch(
    "/{clip_id}",
    response_model=ClipResponse,
    summary="Update clip metadata or settings",
)
async def update_clip(
    clip_id: str,
    payload: ClipUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clip = await _get_owned_clip(clip_id, current_user.id, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(clip, field, value)

    await db.commit()
    await db.refresh(clip)
    return clip


@router.post(
    "/{clip_id}/render",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Render the clip to MP4 (async job)",
)
async def render_clip(
    clip_id: str,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clip = await _get_owned_clip(clip_id, current_user.id, db)

    job = Job(
        project_id=clip.project_id,
        job_type="clip_render",
        status="pending",
        input_data={"clip_id": clip_id},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    try:
        from app.workers.tasks import render_clip_task
        task = render_clip_task.delay(job_id=job.id, clip_id=clip_id)
        job.celery_task_id = task.id
        await db.commit()
        await db.refresh(job)
    except Exception as e:
        logger.warning(
            "Could not enqueue render_clip_task via Celery, running in background task",
            error=str(e),
        )
        background_tasks.add_task(
            render_clip_task.apply,
            kwargs={"job_id": job.id, "clip_id": clip_id},
        )

    return job


@router.post(
    "/{clip_id}/export",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Export the final rendered clip",
)
async def export_clip(
    clip_id: str,
    payload: ExportClipRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clip = await _get_owned_clip(clip_id, current_user.id, db)

    if clip.status not in ("ready", "exported"):
        raise ValidationError(
            f"Clip must be in 'ready' status before export (current: {clip.status})"
        )

    job = Job(
        project_id=clip.project_id,
        job_type="clip_export",
        status="pending",
        input_data={"clip_id": clip_id, **payload.model_dump()},
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    try:
        from app.workers.tasks import export_clip_task
        task = export_clip_task.delay(
            job_id=job.id,
            clip_id=clip_id,
            export_settings=payload.model_dump(),
        )
        job.celery_task_id = task.id
        await db.commit()
        await db.refresh(job)
    except Exception as e:
        logger.warning(
            "Could not enqueue export_clip_task via Celery, running in background task",
            error=str(e),
        )
        background_tasks.add_task(
            export_clip_task.apply,
            kwargs={
                "job_id": job.id,
                "clip_id": clip_id,
                "export_settings": payload.model_dump(),
            },
        )

    return job


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _get_owned_project(project_id: str, user_id: str, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project: Project | None = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", project_id)
    if project.user_id != user_id:
        raise ForbiddenError("You do not have access to this project")
    return project


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
