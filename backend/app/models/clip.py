"""Clip ORM Model — generated video clip candidates."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Time range in source video
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)

    # Content
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Transcript segments that fall within this clip
    segments: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Scoring
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rank: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Rendered output
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    public_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Status: candidate | rendering | ready | exported | failed
    status: Mapped[str] = mapped_column(
        String(50), default="candidate", nullable=False, index=True
    )

    # Whether user selected/approved this clip
    is_selected: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Rendering settings applied
    render_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="clips")  # noqa: F821
    editing_project: Mapped["EditingProject | None"] = relationship(  # noqa: F821
        "EditingProject",
        back_populates="clip",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Clip id={self.id!r} start={self.start_time} end={self.end_time} score={self.score:.2f}>"
