"""Video ORM Model — stores upload metadata and storage path."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(50), default="local", nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # FFprobe-extracted metadata
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    video_codec: Mapped[str | None] = mapped_column(String(50), nullable=True)
    audio_codec: Mapped[str | None] = mapped_column(String(50), nullable=True)
    has_audio: Mapped[bool] = mapped_column(default=True, nullable=False)
    bitrate_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Raw FFprobe JSON (complete metadata)
    raw_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Processing state
    status: Mapped[str] = mapped_column(
        String(50), default="uploaded", nullable=False, index=True
    )  # uploaded | processing | ready | failed

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
    project: Mapped["Project"] = relationship("Project", back_populates="videos")  # noqa: F821
    transcript: Mapped["Transcript | None"] = relationship(  # noqa: F821
        "Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Video id={self.id!r} filename={self.original_filename!r}>"
