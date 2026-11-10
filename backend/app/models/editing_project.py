"""EditingProject ORM Model — timeline and export settings for a clip."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EditingProject(Base):
    __tablename__ = "editing_projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    clip_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("clips.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Timeline data: tracks, captions, effects, trim points
    timeline_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Export settings: resolution, format, quality, etc.
    export_settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Version for undo/redo (increment on save)
    version: Mapped[int] = mapped_column(default=1, nullable=False)

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
    clip: Mapped["Clip"] = relationship("Clip", back_populates="editing_project")  # noqa: F821

    def __repr__(self) -> str:
        return f"<EditingProject id={self.id!r} clip_id={self.clip_id!r} version={self.version}>"
