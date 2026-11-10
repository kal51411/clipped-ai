"""
Whisper Transcription Service (faster-whisper)
Produces timestamped segments from a WAV audio file.
Model is loaded once and cached globally for the process lifetime.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from app.core.config import settings
from app.core.exceptions import TranscriptionError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Compatibility patch: faster-whisper passes metadata_errors="ignore" to av.open,
# which was removed in PyAV >= 14. Strip it safely.
try:
    import av
    _orig_av_open = av.open
    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _orig_av_open(*args, **kwargs)
    av.open = _safe_av_open
except Exception:
    pass

# Module-level model cache — avoids reloading on every request
_model = None
_model_size: Optional[str] = None


def _get_model():
    """Lazy-load faster-whisper model, caching it for the process lifetime."""
    global _model, _model_size

    if _model is not None and _model_size == settings.WHISPER_MODEL_SIZE:
        return _model

    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise TranscriptionError(
            "faster-whisper is not installed. Run: pip install faster-whisper"
        ) from e

    logger.info(
        "Loading Whisper model",
        size=settings.WHISPER_MODEL_SIZE,
        device=settings.WHISPER_DEVICE,
        compute_type=settings.WHISPER_COMPUTE_TYPE,
    )

    _model = WhisperModel(
        settings.WHISPER_MODEL_SIZE,
        device=settings.WHISPER_DEVICE,
        compute_type=settings.WHISPER_COMPUTE_TYPE,
    )
    _model_size = settings.WHISPER_MODEL_SIZE
    logger.info("Whisper model loaded successfully")
    return _model


@dataclass
class TranscriptWord:
    word: str
    start: float
    end: float
    probability: float


@dataclass
class TranscriptSegment:
    id: int
    start: float
    end: float
    text: str
    words: List[TranscriptWord]
    avg_logprob: float
    no_speech_prob: float


@dataclass
class TranscriptionResult:
    full_text: str
    segments: List[TranscriptSegment]
    language: str
    model_used: str


def transcribe_audio(audio_path: str) -> TranscriptionResult:
    """
    Transcribe audio file using faster-whisper.
    Returns timestamped segments with word-level timestamps where available.

    Args:
        audio_path: Path to a WAV file (16kHz mono recommended)

    Returns:
        TranscriptionResult with full text and timestamped segments
    """
    if not os.path.exists(audio_path):
        raise TranscriptionError(f"Audio file not found: {audio_path}")

    if os.path.getsize(audio_path) == 0:
        raise TranscriptionError("Audio file is empty — video may have no audio track")

    model = _get_model()

    logger.info("Starting transcription", audio_path=audio_path)

    try:
        segments_iter, info = model.transcribe(
            audio_path,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,          # filter out silence
            vad_parameters={
                "min_silence_duration_ms": 500,
            },
            condition_on_previous_text=True,
            language=None,            # auto-detect language
        )

        logger.info(
            "Transcription started",
            language=info.language,
            language_probability=round(info.language_probability, 3),
        )

        segments: List[TranscriptSegment] = []
        full_text_parts: List[str] = []

        for i, seg in enumerate(segments_iter):
            words: List[TranscriptWord] = []
            if seg.words:
                for w in seg.words:
                    words.append(
                        TranscriptWord(
                            word=w.word,
                            start=round(w.start, 3),
                            end=round(w.end, 3),
                            probability=round(w.probability, 4),
                        )
                    )

            segment = TranscriptSegment(
                id=i,
                start=round(seg.start, 3),
                end=round(seg.end, 3),
                text=seg.text.strip(),
                words=words,
                avg_logprob=round(seg.avg_logprob, 4),
                no_speech_prob=round(seg.no_speech_prob, 4),
            )
            segments.append(segment)
            full_text_parts.append(seg.text.strip())

        full_text = " ".join(full_text_parts)
        model_name = f"faster-whisper-{settings.WHISPER_MODEL_SIZE}"

        logger.info(
            "Transcription complete",
            segments=len(segments),
            language=info.language,
            total_chars=len(full_text),
        )

        return TranscriptionResult(
            full_text=full_text,
            segments=segments,
            language=info.language,
            model_used=model_name,
        )

    except Exception as e:
        if "audio" in str(e).lower() or "wav" in str(e).lower():
            raise TranscriptionError(f"Audio processing error: {e}") from e
        raise TranscriptionError(f"Transcription failed: {e}") from e


def segments_to_dict(segments: List[TranscriptSegment]) -> List[dict]:
    """Serialize TranscriptSegment list to JSON-serializable dicts."""
    return [
        {
            "id": s.id,
            "start": s.start,
            "end": s.end,
            "text": s.text,
            "avg_logprob": s.avg_logprob,
            "no_speech_prob": s.no_speech_prob,
            "words": [
                {
                    "word": w.word,
                    "start": w.start,
                    "end": w.end,
                    "probability": w.probability,
                }
                for w in s.words
            ],
        }
        for s in segments
    ]
