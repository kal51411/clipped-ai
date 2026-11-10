"""
Clip Rendering Pipeline
Orchestrates: trim → vertical reframe → subtitle burn-in → MP4 output.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.exceptions import VideoProcessingError
from app.core.logging_config import get_logger
from app.video.captions.subtitle_generator import generate_ass
from app.video.processing.ffmpeg import (
    burn_subtitles,
    convert_to_vertical,
    generate_thumbnail,
    trim_video,
)

logger = get_logger(__name__)


def render_clip(
    source_video_path: str,
    start_time: float,
    end_time: float,
    output_dir: str,
    segments: Optional[list] = None,
    include_captions: bool = True,
    caption_style: Optional[dict] = None,
    vertical: bool = True,
    clip_id: Optional[str] = None,
) -> dict:
    """
    Full rendering pipeline for a clip.

    Steps:
    1. Trim the source video to [start_time, end_time]
    2. Convert to 9:16 vertical format (if vertical=True)
    3. Generate and burn subtitles (if include_captions=True and segments provided)
    4. Generate thumbnail
    5. Clean up temp files

    Returns dict with paths: {output_path, thumbnail_path}
    """
    clip_id = clip_id or str(uuid.uuid4())
    tmp_dir = Path(settings.TEMP_DIR) / f"{clip_id}_{uuid.uuid4().hex[:8]}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── Step 1: Trim ─────────────────────────────────────────────────────
        trimmed_path = str(tmp_dir / "trimmed.mp4")
        logger.info("Trimming clip", start=start_time, end=end_time)
        trim_video(
            input_path=source_video_path,
            output_path=trimmed_path,
            start_time=start_time,
            end_time=end_time,
            re_encode=include_captions,  # re-encode if adding captions
        )

        current_path = trimmed_path

        # ── Step 2: Vertical conversion ───────────────────────────────────────
        if vertical:
            vertical_path = str(tmp_dir / "vertical.mp4")
            logger.info("Converting to vertical 9:16")
            convert_to_vertical(
                input_path=current_path,
                output_path=vertical_path,
            )
            current_path = vertical_path

        # ── Step 3: Subtitles ─────────────────────────────────────────────────
        if include_captions and segments:
            style = caption_style or {}
            subtitle_path = str(tmp_dir / f"captions.ass")
            generate_ass(
                segments=segments,
                output_path=subtitle_path,
                start_offset=start_time,
                font_size=style.get("font_size", 28),
                bold=style.get("bold", True),
                primary_color=style.get("primary_color", "&H00FFFFFF"),
                outline_color=style.get("outline_color", "&H00000000"),
                outline_width=style.get("outline_width", 2.5),
                alignment=style.get("alignment", 2),
                margin_v=style.get("margin_v", 60),
            )

            captioned_path = str(tmp_dir / "captioned.mp4")
            logger.info("Burning subtitles")
            burn_subtitles(
                input_path=current_path,
                output_path=captioned_path,
                subtitle_path=subtitle_path,
            )
            current_path = captioned_path

        # ── Step 4: Move to output ─────────────────────────────────────────────
        final_output = str(out_dir / f"{clip_id}.mp4")
        os.rename(current_path, final_output)

        # ── Step 5: Thumbnail ──────────────────────────────────────────────────
        thumbnail_output = str(out_dir / f"{clip_id}_thumb.jpg")
        try:
            generate_thumbnail(
                video_path=final_output,
                output_path=thumbnail_output,
                timestamp=1.0,
                width=360,
            )
        except Exception as e:
            logger.warning("Thumbnail generation failed", error=str(e))
            thumbnail_output = None

        logger.info("Clip rendering complete", output=final_output)
        return {
            "output_path": final_output,
            "thumbnail_path": thumbnail_output,
        }

    finally:
        # Clean up temp directory
        _cleanup_dir(str(tmp_dir))


def _cleanup_dir(path: str) -> None:
    """Safely remove a temporary directory and its contents."""
    import shutil
    try:
        if os.path.exists(path):
            shutil.rmtree(path, ignore_errors=True)
    except Exception as e:
        logger.warning("Failed to cleanup temp dir", path=path, error=str(e))
