"""Job ORM Model — background processing job tracker."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Job type: transcription | clip_generation | export
    job_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Status: pending | running | completed | failed | cancelled
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )
    # 0.0 → 1.0
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    progress_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Celery task ID for tracking
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    # Input/output metadata stored as JSON
    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="jobs")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Job id={self.id!r} type={self.job_type!r} status={self.status!r}>"
