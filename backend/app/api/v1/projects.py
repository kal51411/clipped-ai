"""
Projects router
POST   /api/v1/projects
GET    /api/v1/projects
GET    /api/v1/projects/{project_id}
PATCH  /api/v1/projects/{project_id}
DELETE /api/v1/projects/{project_id}
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.logging_config import get_logger
from app.core.security import get_current_user
from app.models.project import Project
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    QuickYoutubeRequest,
    QuickYoutubeResponse,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = Project(
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.post(
    "/quick-youtube",
    response_model=QuickYoutubeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="One-click YouTube link to short-form AI video generation",
)
async def quick_youtube(
    payload: QuickYoutubeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import asyncio
    import uuid
    from pathlib import Path
    from app.core.config import settings
    from app.models.job import Job
    from app.models.video import Video
    from app.video.ingestion.url_downloader import extract_url_metadata
    from app.workers.tasks import pipeline_from_video_task

    video_id = str(uuid.uuid4())
    safe_name = f"{video_id}.mp4"
    storage_root = Path(settings.LOCAL_STORAGE_PATH) / "videos"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage_path = str(storage_root / safe_name)

    # 1. Quickly extract video metadata (title, duration) in ~1s without blocking on file download
    info = await asyncio.to_thread(extract_url_metadata, payload.url)
    video_title = payload.title or info.get("title") or f"YouTube Video ({video_id[:8]})"

    # 2. Create Project immediately
    project = Project(
        user_id=current_user.id,
        title=video_title,
        description=f"Auto-generated from YouTube: {payload.url}",
        prompt=payload.prompt,
        status="processing",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # 3. Create Video record
    video = Video(
        id=video_id,
        project_id=project.id,
        original_filename=f"{video_title}.mp4",
        storage_path=storage_path,
        storage_backend="local",
        file_size_bytes=0,
        mime_type="video/mp4",
        status="downloading",
    )
    db.add(video)

    # 4. Create Job record
    job = Job(
        project_id=project.id,
        job_type="youtube_to_shorts",
        status="running",
        progress=0.1,
        progress_message="Starting fast video stream download from YouTube...",
        input_data={
            "url": payload.url,
            "prompt": payload.prompt,
            "target_duration_seconds": payload.target_duration_seconds,
            "num_candidates": payload.num_candidates,
        },
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 5. Enqueue background pipeline with video_url
    task_kwargs = {
        "job_id": job.id,
        "video_id": video.id,
        "project_id": project.id,
        "prompt": payload.prompt or "Find the most interesting, viral, and engaging moments",
        "target_duration": payload.target_duration_seconds or 30,
        "num_candidates": payload.num_candidates or 5,
        "video_url": payload.url,
    }

    try:
        task = pipeline_from_video_task.delay(**task_kwargs)
        job.celery_task_id = task.id
        await db.commit()
        logger.info("Enqueued pipeline_from_video_task", job_id=job.id, task_id=task.id)
    except Exception as e:
        logger.warning(
            "Could not enqueue pipeline_from_video_task via Celery, running in background task",
            error=str(e),
        )
        async def _run_pipeline_in_thread():
            await asyncio.to_thread(pipeline_from_video_task.apply, kwargs=task_kwargs)

        background_tasks.add_task(_run_pipeline_in_thread)

    return QuickYoutubeResponse(
        project=ProjectResponse.model_validate(project),
        video_id=video.id,
        job_id=job.id,
        message="YouTube video processing started! Redirecting to workspace...",
    )




@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List current user's projects",
)
async def list_projects(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Project).where(Project.user_id == current_user.id)
    if status:
        query = query.where(Project.status == status)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginate
    query = query.order_by(Project.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    projects = result.scalars().all()

    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a project by ID",
)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_owned_project(project_id, current_user.id, db)
    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project fields",
)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_owned_project(project_id, current_user.id, db)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await _get_owned_project(project_id, current_user.id, db)
    await db.delete(project)
    await db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _get_owned_project(
    project_id: str, user_id: str, db: AsyncSession
) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project: Project | None = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", project_id)
    if project.user_id != user_id:
        raise ForbiddenError("You do not have access to this project")
    return project
