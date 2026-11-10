"""
URL & YouTube Video Downloader
Uses yt-dlp to safely fetch authorized online video/audio streams into local storage.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from app.core.exceptions import VideoProcessingError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def extract_url_metadata(url: str) -> Dict[str, Any]:
    """
    Quickly extracts video metadata (title, duration, etc.) without downloading the video.
    Returns in 1-2 seconds.
    """
    try:
        import yt_dlp
    except ImportError as e:
        raise VideoProcessingError(
            "yt-dlp is not installed. Run: pip install yt-dlp"
        ) from e

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": False,
        "no_warnings": True,
        "socket_timeout": 10,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return {"title": "Imported Video", "duration": 0}
            return {
                "title": info.get("title", "Imported Video"),
                "duration": info.get("duration", 0),
                "extractor": info.get("extractor", "generic"),
                "uploader": info.get("uploader"),
                "thumbnail": info.get("thumbnail"),
            }
    except Exception as e:
        logger.warning("Could not extract full video info via yt-dlp", error=str(e))
        return {"title": "YouTube Video", "duration": 0}


def download_video_from_url(url: str, output_path: str) -> Dict[str, Any]:
    """
    Downloads a video from a URL (YouTube, Vimeo, direct MP4, etc.)
    using yt-dlp into the specified output_path.
    Optimized for fast download (720p vertical-ready format).
    """
    try:
        import yt_dlp
    except ImportError as e:
        raise VideoProcessingError(
            "yt-dlp is not installed. Run: pip install yt-dlp"
        ) from e

    # Ensure parent directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Base path without extension for yt-dlp outtmpl
    base_output = os.path.splitext(output_path)[0]

    ydl_opts = {
        # Prioritize 720p / 480p for 10x faster download speed and low CPU overhead
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=480]/best",
        "outtmpl": f"{base_output}.%(ext)s",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "overwrites": True,
        "concurrent_fragment_downloads": 4,
        "buffersize": 1024 * 1024,
    }

    logger.info("Downloading video from URL", url=url)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                raise VideoProcessingError(f"Could not extract video metadata from URL: {url}")

            downloaded_file = ydl.prepare_filename(info)
            # Ensure the merged mp4 format is pointed to
            if not downloaded_file.endswith(".mp4"):
                merged = f"{os.path.splitext(downloaded_file)[0]}.mp4"
                if os.path.exists(merged):
                    downloaded_file = merged

            # If downloaded file doesn't match target output_path exactly, rename it
            if os.path.exists(downloaded_file) and downloaded_file != output_path:
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(downloaded_file, output_path)

            file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0

            logger.info(
                "Video downloaded successfully",
                title=info.get("title"),
                duration=info.get("duration"),
                size_bytes=file_size,
            )

            return {
                "title": info.get("title", "Imported Video"),
                "duration": info.get("duration", 0),
                "extractor": info.get("extractor", "generic"),
                "uploader": info.get("uploader"),
                "file_size_bytes": file_size,
                "file_path": output_path,
            }

    except Exception as e:
        logger.error("Failed to download video from URL", url=url, error=str(e))
        raise VideoProcessingError(f"Failed to import video from URL: {e}") from e
