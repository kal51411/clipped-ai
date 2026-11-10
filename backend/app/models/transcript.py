"""Transcript ORM Model — stores timestamped Whisper segments."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    video_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # Full text of transcript
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON array of {start, end, text, words} segments
    segments: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Detected language
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Transcription model used
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Status
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )  # pending | processing | completed | failed | no_audio
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    video: Mapped["Video"] = relationship("Video", back_populates="transcript")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Transcript id={self.id!r} video_id={self.video_id!r} status={self.status!r}>"
