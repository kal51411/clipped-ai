"""Job Pydantic Schemas"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class JobStatus(str):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    project_id: str
    job_type: str
    status: str
    progress: float
    progress_message: Optional[str] = None
    error_message: Optional[str] = None
    celery_task_id: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
