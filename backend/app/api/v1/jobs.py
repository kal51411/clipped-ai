"""
Jobs router
GET /api/v1/jobs/{job_id}             — poll job status
GET /api/v1/jobs?project_id=...       — list all jobs for a project
DELETE /api/v1/jobs/{job_id}/cancel   — cancel a pending/running job
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.core.security import get_current_user
from app.models.job import Job
from app.models.project import Project
from app.models.user import User
from app.schemas.job import JobResponse

router = APIRouter()


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Poll the status of a background job",
)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _get_owned_job(job_id, current_user.id, db)
    return job


@router.get(
    "",
    response_model=List[JobResponse],
    summary="List all jobs for a project",
)
async def list_jobs(
    project_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify project ownership
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project: Project | None = proj_result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", project_id)
    if project.user_id != current_user.id:
        raise ForbiddenError("You do not have access to this project")

    result = await db.execute(
        select(Job)
        .where(Job.project_id == project_id)
        .order_by(Job.created_at.desc())
    )
    return result.scalars().all()


@router.delete(
    "/{job_id}/cancel",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel a pending or running job",
)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await _get_owned_job(job_id, current_user.id, db)

    if job.status not in ("pending", "running"):
        raise ValidationError(
            f"Cannot cancel a job in '{job.status}' state"
        )

    # Revoke Celery task if present
    if job.celery_task_id:
        try:
            from app.workers.celery_app import celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=True)
        except Exception:
            pass

    job.status = "cancelled"
    await db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _get_owned_job(job_id: str, user_id: str, db: AsyncSession) -> Job:
    result = await db.execute(
        select(Job)
        .join(Project, Job.project_id == Project.id)
        .where(Job.id == job_id, Project.user_id == user_id)
    )
    job: Job | None = result.scalar_one_or_none()
    if not job:
        raise NotFoundError("Job", job_id)
    return job
