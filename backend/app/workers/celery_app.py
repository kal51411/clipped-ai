"""
Celery Application Configuration
Broker: Redis
Result Backend: Redis (separate DB)
"""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "clipped_ai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # Fair scheduling — important for long video tasks
    task_soft_time_limit=3600,     # 1 hour soft limit
    task_time_limit=7200,          # 2 hour hard limit
    result_expires=86400 * 7,      # Keep results for 7 days
    task_default_queue="celery",
    task_routes={
        "app.workers.tasks.*": {"queue": "celery"},
    },
)
