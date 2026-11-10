"""
FFmpeg wrapper — safe subprocess calls for video processing.
All commands use parameter lists (no shell injection risk).
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.exceptions import VideoProcessingError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def _run(cmd: List[str], check: bool = True, timeout: int = 3600) -> subprocess.CompletedProcess:
    """Run an FFmpeg subprocess safely."""
    logger.debug("Running command", cmd=" ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if check and result.returncode != 0:
            raise VideoProcessingError(
                f"FFmpeg failed (exit {result.returncode})",
                detail=result.stderr[-2000:],
            )
        return result
    except subprocess.TimeoutExpired as e:
        raise VideoProcessingError(f"FFmpeg timed out after {timeout}s") from e
    except FileNotFoundError as e:
        raise VideoProcessingError(
            f"FFmpeg not found at '{settings.FFMPEG_PATH}'. Install ffmpeg."
        ) from e


# ── Metadata Extraction ───────────────────────────────────────────────────────
def probe_video(video_path: str) -> Dict[str, Any]:
    """
    Run ffprobe and return a dict with video metadata.
    Keys: duration_seconds, width, height, fps, video_codec, audio_codec,
          has_audio, bitrate_kbps, raw
    """
    cmd = [
        settings.FFPROBE_PATH,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        video_path,
    ]
    result = _run(cmd, check=True)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise VideoProcessingError("FFprobe returned invalid JSON") from e

    streams = data.get("streams", [])
    fmt = data.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = float(fmt.get("duration") or 0)
    if not duration and video_stream:
        duration = float(video_stream.get("duration") or 0)

    fps: Optional[float] = None
    if video_stream:
        r_frame_rate = video_stream.get("r_frame_rate", "0/1")
        try:
            num, den = r_frame_rate.split("/")
            fps = float(num) / float(den) if float(den) != 0 else None
        except (ValueError, ZeroDivisionError):
            fps = None

    bitrate_bps = int(fmt.get("bit_rate") or 0)
    bitrate_kbps = bitrate_bps // 1000 if bitrate_bps else None

    return {
        "duration_seconds": duration,
        "width": int(video_stream.get("width", 0)) if video_stream else None,
        "height": int(video_stream.get("height", 0)) if video_stream else None,
        "fps": round(fps, 3) if fps else None,
        "video_codec": video_stream.get("codec_name") if video_stream else None,
        "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
        "has_audio": audio_stream is not None,
        "bitrate_kbps": bitrate_kbps,
        "raw": data,
    }


# ── Audio Extraction ──────────────────────────────────────────────────────────
def extract_audio(
    video_path: str,
    output_path: str,
    sample_rate: int = 16000,
    channels: int = 1,
) -> str:
    """
    Extract audio from video as 16kHz mono WAV (optimal for Whisper).
    Returns the output_path on success.
    """
    cmd = [
        settings.FFMPEG_PATH,
        "-y",                    # overwrite
        "-i", video_path,
        "-vn",                   # no video
        "-ar", str(sample_rate), # sample rate
        "-ac", str(channels),    # mono
        "-acodec", "pcm_s16le",  # 16-bit PCM WAV
        output_path,
    ]
    _run(cmd, check=True)
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise VideoProcessingError("Audio extraction produced empty file")
    logger.info("Audio extracted", output=output_path)
    return output_path


# ── Video Trimming ────────────────────────────────────────────────────────────
def trim_video(
    input_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
    re_encode: bool = False,
) -> str:
    """
    Trim a video to [start_time, end_time].
    Uses stream copy by default (fast, no quality loss).
    Set re_encode=True if the source has variable frame rates or captions need to be burned.
    """
    duration = end_time - start_time
    if duration <= 0:
        raise VideoProcessingError(f"Invalid trim range: {start_time} → {end_time}")

    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-ss", str(start_time),
        "-i", input_path,
        "-t", str(duration),
    ]

    if re_encode:
        cmd += [
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
        ]
    else:
        cmd += ["-c", "copy"]

    cmd.append(output_path)
    _run(cmd, check=True)
    logger.info("Video trimmed", start=start_time, end=end_time, output=output_path)
    return output_path


# ── Vertical 9:16 Crop ────────────────────────────────────────────────────────
def convert_to_vertical(
    input_path: str,
    output_path: str,
    target_width: int = 1080,
    target_height: int = 1920,
) -> str:
    """
    Convert horizontal video to 9:16 vertical format via centre crop.
    Strategy:
    1. Scale so height matches target_height (preserving aspect ratio)
    2. Centre-crop to target_width x target_height
    3. If source is already taller than wide, scale width to target_width and centre-crop height
    """
    # Determine source dimensions
    meta = probe_video(input_path)
    src_w = meta.get("width") or 1920
    src_h = meta.get("height") or 1080

    # Build vf filter chain
    # Scale to fill target height, then crop width
    scale_filter = f"scale=-2:{target_height}"
    crop_filter = f"crop={target_width}:{target_height}"

    # For portrait source (height > width), scale width first
    if src_h > src_w:
        scale_filter = f"scale={target_width}:-2"
        crop_filter = f"crop={target_width}:{target_height}"

    vf = f"{scale_filter},{crop_filter}"

    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]
    _run(cmd, check=True)
    logger.info(
        "Converted to vertical",
        target=f"{target_width}x{target_height}",
        output=output_path,
    )
    return output_path


# ── Caption Burn-in ───────────────────────────────────────────────────────────
def burn_subtitles(
    input_path: str,
    output_path: str,
    subtitle_path: str,
    font_size: int = 24,
    font_color: str = "white",
    outline_color: str = "black",
    outline_width: int = 2,
    position: str = "bottom",  # bottom | center | top
) -> str:
    """
    Burn subtitles from an .ass or .srt file into the video.
    Uses libass for high-quality rendering.
    """
    # Position mapping
    pos_map = {"top": "&H10&", "center": "&H20&", "bottom": "&H40&"}
    alignment = pos_map.get(position, "&H40&")

    # Escape the subtitle path for FFmpeg filter
    safe_sub_path = subtitle_path.replace("\\", "/").replace(":", "\\:")

    sub_filter = (
        f"subtitles='{safe_sub_path}':force_style='"
        f"Fontsize={font_size},"
        f"PrimaryColour=&H{_color_to_ass(font_color)}&,"
        f"OutlineColour=&H{_color_to_ass(outline_color)}&,"
        f"BorderStyle=1,"
        f"Outline={outline_width},"
        f"Alignment={alignment}'"
    )

    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-i", input_path,
        "-vf", sub_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path,
    ]
    _run(cmd, check=True)
    logger.info("Subtitles burned in", output=output_path)
    return output_path


def _color_to_ass(color_name: str) -> str:
    """Convert color name to ASS hex format (BBGGRR)."""
    colors = {
        "white": "FFFFFF",
        "black": "000000",
        "yellow": "00FFFF",
        "red": "0000FF",
        "blue": "FF0000",
        "green": "00FF00",
    }
    rgb = colors.get(color_name.lower(), "FFFFFF")
    # ASS format is BBGGRR
    r, g, b = rgb[0:2], rgb[2:4], rgb[4:6]
    return f"{b}{g}{r}"


# ── Generate Thumbnail ─────────────────────────────────────────────────────────
def generate_thumbnail(
    video_path: str,
    output_path: str,
    timestamp: float = 1.0,
    width: int = 480,
) -> str:
    """Extract a single frame as a JPEG thumbnail."""
    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-ss", str(timestamp),
        "-i", video_path,
        "-vframes", "1",
        "-vf", f"scale={width}:-1",
        "-q:v", "5",
        output_path,
    ]
    _run(cmd, check=True)
    return output_path
