"""
Celery Background Tasks
Glues together all services: ingest → transcribe → AI → render → export.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from celery import Task
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def _get_sync_db():
    """Get a synchronous SQLAlchemy session for use inside Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.DATABASE_SYNC_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _update_job(session: Session, job_id: str, **kwargs) -> None:
    """Update a job record in the database."""
    from app.models.job import Job

    job = session.query(Job).filter(Job.id == job_id).first()
    if job:
        for k, v in kwargs.items():
            setattr(job, k, v)
        session.commit()


# ─────────────────────────────────────────────────────────────────────────────
# TASK 1: Process Video (metadata extraction + audio extraction + transcription)
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(bind=True, name="app.workers.tasks.process_video_task")
def process_video_task(self: Task, video_id: str, project_id: str) -> Dict[str, Any]:
    """
    Background task: extract metadata and transcribe a video.
    Updates Video and Transcript records in the database.
    """
    from app.models.video import Video
    from app.models.transcript import Transcript
    from app.models.job import Job
    from app.video.processing.ffmpeg import probe_video, extract_audio
    from app.ai.transcription.whisper_service import transcribe_audio, segments_to_dict

    db = _get_sync_db()
    job = None

    try:
        # Create a job record
        job = Job(
            project_id=project_id,
            job_type="video_processing",
            status="running",
            celery_task_id=getattr(self.request, "id", None) if getattr(self, "request", None) else None,
            started_at=datetime.now(timezone.utc),
        )
        db.add(job)
        db.commit()

        # ── Step 1: Fetch video record ────────────────────────────────────────
        video: Video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video {video_id} not found in database")

        video.status = "processing"
        db.commit()

        _update_job(db, job.id, progress=0.1, progress_message="Extracting video metadata")

        # ── Step 2: Extract metadata via ffprobe ──────────────────────────────
        meta = probe_video(video.storage_path)
        video.duration_seconds = meta["duration_seconds"]
        video.width = meta["width"]
        video.height = meta["height"]
        video.fps = meta["fps"]
        video.video_codec = meta["video_codec"]
        video.audio_codec = meta["audio_codec"]
        video.has_audio = meta["has_audio"]
        video.bitrate_kbps = meta["bitrate_kbps"]
        video.raw_metadata = meta["raw"]
        db.commit()

        logger.info("Video metadata extracted", video_id=video_id, duration=meta["duration_seconds"])

        # ── Step 3: Extract audio ─────────────────────────────────────────────
        _update_job(db, job.id, progress=0.3, progress_message="Extracting audio")

        transcript_record = Transcript(
            video_id=video_id,
            status="processing",
            model_used=f"faster-whisper-{settings.WHISPER_MODEL_SIZE}",
        )
        db.add(transcript_record)
        db.commit()

        if not video.has_audio:
            transcript_record.status = "no_audio"
            transcript_record.full_text = ""
            transcript_record.segments = []
            db.commit()
            video.status = "ready"
            db.commit()
            _update_job(
                db, job.id,
                status="completed",
                progress=1.0,
                progress_message="Video has no audio track. Skipping transcription.",
                completed_at=datetime.now(timezone.utc),
                result_data={"transcript_status": "no_audio"},
            )
            return {"status": "completed", "transcript": "no_audio"}

        # Create temp audio file
        tmp_dir = Path(settings.TEMP_DIR) / f"proc_{video_id}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        audio_path = str(tmp_dir / "audio.wav")

        try:
            extract_audio(video.storage_path, audio_path)
        except Exception as e:
            transcript_record.status = "failed"
            transcript_record.error_message = str(e)
            db.commit()
            raise

        # ── Step 4: Transcribe ────────────────────────────────────────────────
        _update_job(db, job.id, progress=0.5, progress_message="Transcribing audio (this may take a few minutes)")

        result = transcribe_audio(audio_path)

        transcript_record.full_text = result.full_text
        transcript_record.segments = segments_to_dict(result.segments)
        transcript_record.language = result.language
        transcript_record.model_used = result.model_used
        transcript_record.status = "completed"
        db.commit()

        # Clean up audio file
        import shutil
        shutil.rmtree(str(tmp_dir), ignore_errors=True)

        video.status = "ready"
        db.commit()

        _update_job(
            db, job.id,
            status="completed",
            progress=1.0,
            progress_message="Transcription complete",
            completed_at=datetime.now(timezone.utc),
            result_data={
                "transcript_id": transcript_record.id,
                "language": result.language,
                "segments": len(result.segments),
            },
        )

        logger.info("Video processing complete", video_id=video_id, segments=len(result.segments))
        return {"status": "completed", "transcript_id": transcript_record.id}

    except Exception as e:
        logger.exception("Video processing failed", video_id=video_id, error=str(e))
        if job:
            _update_job(
                db, job.id,
                status="failed",
                error_message=str(e),
                completed_at=datetime.now(timezone.utc),
            )
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# TASK 2: Generate Clips (AI pipeline)
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(bind=True, name="app.workers.tasks.generate_clips_task")
def generate_clips_task(
    self: Task,
    job_id: str,
    project_id: str,
    prompt: str,
    target_duration: int = 60,
    num_candidates: int = 5,
) -> Dict[str, Any]:
    """
    Background task: run the full AI clip selection pipeline.
    1. Load transcript
    2. Parse prompt with Gemini
    3. Generate candidates
    4. Score candidates
    5. Store top clips in DB
    """
    from app.models.clip import Clip
    from app.models.project import Project
    from app.models.transcript import Transcript
    from app.models.video import Video
    from app.ai.understanding.prompt_parser import parse_prompt
    from app.ai.clip_selection.candidate_generator import generate_candidates
    from app.ai.clip_selection.scorer import score_candidates
    from app.video.rendering.renderer import render_clip

    db = _get_sync_db()

    try:
        _update_job(db, job_id, status="running", started_at=datetime.now(timezone.utc))
        _update_job(db, job_id, progress=0.1, progress_message="Loading transcript")

        # Load project + video + transcript
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        video = db.query(Video).filter(Video.project_id == project_id).first()
        if not video:
            raise ValueError("No video found for project")

        transcript = db.query(Transcript).filter(Transcript.video_id == video.id).first()
        if not transcript or not transcript.segments:
            raise ValueError("No transcript available. Ensure video processing is complete.")

        segments = transcript.segments or []
        video_duration = video.duration_seconds or 0

        # ── Parse prompt ──────────────────────────────────────────────────────
        _update_job(db, job_id, progress=0.25, progress_message="Understanding your prompt")
        intent = parse_prompt(prompt)
        logger.info("Prompt parsed", topic=intent.topic, keywords=intent.keywords)

        # ── Generate candidates ───────────────────────────────────────────────
        _update_job(db, job_id, progress=0.4, progress_message="Finding candidate segments")
        candidates = generate_candidates(
            segments=segments,
            target_duration=intent.target_duration_seconds or target_duration,
            video_duration=video_duration,
        )

        if not candidates:
            raise ValueError(
                "No suitable clip candidates found. The video may be too short "
                "or the transcript too sparse for the requested duration."
            )

        logger.info("Candidates generated", count=len(candidates))

        # ── Score candidates ──────────────────────────────────────────────────
        _update_job(db, job_id, progress=0.65, progress_message="Scoring and ranking clips")
        scored = score_candidates(
            candidates=candidates,
            intent=intent,
            video_duration=video_duration,
            use_gemini_rerank=settings.GEMINI_ENABLED,
        )

        # ── Store and render top clips in DB ──────────────────────────────────
        _update_job(db, job_id, progress=0.8, progress_message="Rendering playable clips")
        top_clips = scored[:num_candidates]
        clip_ids = []
        rendered_count = 0

        for index, scored_clip in enumerate(top_clips):
            cand = scored_clip.candidate
            clip = Clip(
                project_id=project_id,
                start_time=cand.start_time,
                end_time=cand.end_time,
                duration=cand.duration,
                transcript_text=cand.text,
                segments=cand.segments,
                score=scored_clip.score,
                score_breakdown=scored_clip.score_breakdown,
                rank=scored_clip.rank,
                status="rendering",
            )
            db.add(clip)
            db.flush()
            clip_ids.append(clip.id)

            try:
                output_dir = Path(settings.OUTPUT_DIR) / project_id
                result = render_clip(
                    source_video_path=video.storage_path,
                    start_time=clip.start_time,
                    end_time=clip.end_time,
                    output_dir=str(output_dir),
                    segments=clip.segments or [],
                    include_captions=True,
                    clip_id=clip.id,
                )
                clip.storage_path = result["output_path"]
                clip.thumbnail_path = result.get("thumbnail_path")
                clip.public_url = f"/media/output/{project_id}/{clip.id}.mp4"
                clip.status = "ready"
                rendered_count += 1
            except Exception:
                clip.status = "failed"
                logger.exception("Clip candidate render failed", clip_id=clip.id)

            _update_job(
                db,
                job_id,
                progress=0.8 + (0.18 * (index + 1) / max(len(top_clips), 1)),
                progress_message=f"Rendered {index + 1} of {len(top_clips)} clips",
            )

        project.status = "ready"
        db.commit()

        _update_job(
            db, job_id,
            status="completed",
            progress=1.0,
            progress_message=f"Ready: {rendered_count} of {len(top_clips)} clips rendered",
            completed_at=datetime.now(timezone.utc),
            result_data={"clip_ids": clip_ids, "total_candidates": len(scored)},
        )

        logger.info("Clip generation complete", clips=len(top_clips), rendered=rendered_count)
        return {"status": "completed", "clip_ids": clip_ids}

    except Exception as e:
        logger.exception("Clip generation failed", job_id=job_id, error=str(e))
        _update_job(
            db, job_id,
            status="failed",
            error_message=str(e),
            completed_at=datetime.now(timezone.utc),
        )
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# TASK 3: Render Clip
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(bind=True, name="app.workers.tasks.render_clip_task")
def render_clip_task(self: Task, job_id: str, clip_id: str) -> Dict[str, Any]:
    """Background task: render a clip to MP4 (trim + vertical + captions)."""
    from app.models.clip import Clip
    from app.models.video import Video
    from app.video.rendering.renderer import render_clip

    db = _get_sync_db()

    try:
        _update_job(db, job_id, status="running", started_at=datetime.now(timezone.utc))

        clip: Clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            raise ValueError(f"Clip {clip_id} not found")

        video: Video = db.query(Video).filter(Video.project_id == clip.project_id).first()
        if not video:
            raise ValueError("Source video not found")

        _update_job(db, job_id, progress=0.2, progress_message="Starting render")
        clip.status = "rendering"
        db.commit()

        output_dir = Path(settings.OUTPUT_DIR) / clip.project_id
        result = render_clip(
            source_video_path=video.storage_path,
            start_time=clip.start_time,
            end_time=clip.end_time,
            output_dir=str(output_dir),
            segments=clip.segments or [],
            include_captions=True,
            clip_id=clip_id,
        )

        clip.storage_path = result["output_path"]
        clip.thumbnail_path = result.get("thumbnail_path")
        clip.public_url = f"/media/output/{clip.project_id}/{clip.id}.mp4"
        clip.status = "ready"
        db.commit()

        _update_job(
            db, job_id,
            status="completed",
            progress=1.0,
            progress_message="Clip rendered successfully",
            completed_at=datetime.now(timezone.utc),
            result_data={"output_path": result["output_path"]},
        )

        logger.info("Clip render complete", clip_id=clip_id)
        return {"status": "completed", "output_path": result["output_path"]}

    except Exception as e:
        logger.exception("Clip render failed", clip_id=clip_id, error=str(e))
        if clip_id:
            clip = db.query(__import__("app.models.clip", fromlist=["Clip"]).Clip).filter_by(id=clip_id).first()
            if clip:
                clip.status = "failed"
                db.commit()
        _update_job(
            db, job_id,
            status="failed",
            error_message=str(e),
            completed_at=datetime.now(timezone.utc),
        )
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# TASK 4: Export Clip
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(bind=True, name="app.workers.tasks.export_clip_task")
def export_clip_task(
    self: Task,
    job_id: str,
    clip_id: str,
    export_settings: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Background task: export a rendered clip with final quality settings.
    Currently copies the rendered file — extend for format conversion.
    """
    from app.models.clip import Clip

    db = _get_sync_db()

    try:
        _update_job(db, job_id, status="running", started_at=datetime.now(timezone.utc))

        clip: Clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            raise ValueError(f"Clip {clip_id} not found")

        if not clip.storage_path or not os.path.exists(clip.storage_path):
            raise ValueError("Clip has not been rendered yet. Run render first.")

        _update_job(db, job_id, progress=0.5, progress_message="Preparing export")

        clip.status = "exported"
        clip.public_url = f"/media/output/{clip.project_id}/{clip.id}.mp4"
        db.commit()

        _update_job(
            db, job_id,
            status="completed",
            progress=1.0,
            progress_message="Export complete",
            completed_at=datetime.now(timezone.utc),
            result_data={"public_url": clip.public_url},
        )

        return {"status": "completed", "public_url": clip.public_url}

    except Exception as e:
        logger.exception("Export failed", clip_id=clip_id, error=str(e))
        _update_job(
            db, job_id,
            status="failed",
            error_message=str(e),
            completed_at=datetime.now(timezone.utc),
        )
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# TASK 5: End-to-End Pipeline from Video (Download -> Transcribe -> AI Clip Selection)
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(bind=True, name="app.workers.tasks.pipeline_from_video_task")
def pipeline_from_video_task(
    self: Task,
    job_id: str,
    video_id: str,
    project_id: str,
    prompt: str,
    target_duration: int = 30,
    num_candidates: int = 5,
    video_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    End-to-end pipeline:
    1. If video_url is provided, download the video.
    2. Probe metadata & transcribe audio with faster-whisper.
    3. Understand prompt & extract candidate segments with Gemini 2.5 Flash.
    4. Score and rank top short-form clips.
    """
    db = _get_sync_db()
    try:
        # ── Step 0: Download if URL provided ─────────────────────────────────
        if video_url:
            from app.models.video import Video
            from app.video.ingestion.url_downloader import download_video_from_url

            _update_job(
                db,
                job_id,
                status="running",
                progress=0.05,
                progress_message="Downloading 720p video from YouTube...",
                started_at=datetime.now(timezone.utc),
            )
            v = db.query(Video).filter(Video.id == video_id).first()
            if v:
                try:
                    download_video_from_url(video_url, v.storage_path)
                    v.status = "downloaded"
                    v.file_size_bytes = (
                        os.path.getsize(v.storage_path) if os.path.exists(v.storage_path) else 0
                    )
                    db.commit()
                    logger.info("YouTube video downloaded", video_id=video_id, path=v.storage_path)
                except Exception as dl_err:
                    logger.exception("YouTube download failed", error=str(dl_err))
                    raise RuntimeError(f"YouTube download failed: {dl_err}") from dl_err

        _update_job(
            db,
            job_id,
            status="running",
            progress=0.30,
            progress_message="Extracting audio & transcribing speech...",
        )

        # ── Step 1: Probe metadata + transcribe (runs synchronously via .apply) ──
        # Using .apply(kwargs=...) properly handles bind=True Celery tasks inline.
        proc_result = process_video_task.apply(
            kwargs={"video_id": video_id, "project_id": project_id}
        )
        if proc_result.failed():
            raise RuntimeError(f"Transcription failed: {proc_result.result}")

        _update_job(
            db,
            job_id,
            progress=0.70,
            progress_message="Finding best short-form clips with Gemini AI...",
        )

        # ── Step 2: AI Clip Generation with Gemini & ranking ─────────────────
        clips_result = generate_clips_task.apply(
            kwargs={
                "job_id": job_id,
                "project_id": project_id,
                "prompt": prompt,
                "target_duration": target_duration,
                "num_candidates": num_candidates,
            }
        )
        if clips_result.failed():
            raise RuntimeError(f"Clip generation failed: {clips_result.result}")

        result = clips_result.result

        _update_job(
            db,
            job_id,
            status="completed",
            progress=1.0,
            progress_message="Your shorts are ready! 🎬",
            completed_at=datetime.now(timezone.utc),
            result_data=result if isinstance(result, dict) else {"clips": str(result)},
        )

        # Update project status
        from app.models.project import Project
        proj = db.query(Project).filter(Project.id == project_id).first()
        if proj:
            proj.status = "ready"
            db.commit()

        logger.info("Pipeline completed", job_id=job_id, project_id=project_id)
        return result or {}

    except Exception as e:
        logger.exception("Pipeline from video failed", job_id=job_id, error=str(e))
        try:
            _update_job(
                db,
                job_id,
                status="failed",
                error_message=str(e),
                completed_at=datetime.now(timezone.utc),
            )
            # Also mark project failed
            from app.models.project import Project
            proj = db.query(Project).filter(Project.id == project_id).first()
            if proj:
                proj.status = "failed"
                db.commit()
        except Exception:
            pass
        raise
    finally:
        db.close()
