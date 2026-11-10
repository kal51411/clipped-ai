"""
Clip Candidate Generator
Generates candidate clip windows from timestamped transcript segments,
respecting sentence boundaries and target duration.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ClipCandidate:
    start_time: float
    end_time: float
    duration: float
    text: str
    segments: List[dict]
    segment_indices: List[int]


def generate_candidates(
    segments: List[dict],
    target_duration: int = 60,
    video_duration: float = 0.0,
    min_duration: int = 10,
    max_duration: int = 180,
    step_size: int = 5,
) -> List[ClipCandidate]:
    """
    Generate candidate clip windows from transcript segments.

    Strategy:
    - Slide a window across segments looking for natural groupings
    - Each candidate starts at a sentence boundary
    - Each candidate ends at a sentence boundary
    - Target duration ± 25% tolerance
    - No arbitrary mid-sentence cuts

    Args:
        segments: List of transcript segment dicts {id, start, end, text, words}
        target_duration: Desired clip duration in seconds
        video_duration: Total video duration (for validation)
        min_duration: Minimum acceptable clip duration
        max_duration: Maximum acceptable clip duration
        step_size: How many segments to slide each iteration

    Returns:
        List of ClipCandidate objects
    """
    if not segments:
        logger.warning("No segments provided for candidate generation")
        return []

    # Tolerance: accept candidates within ±35% of target
    lower_bound = max(min_duration, target_duration * 0.65)
    upper_bound = min(max_duration, target_duration * 1.35)

    candidates: List[ClipCandidate] = []
    n = len(segments)

    for start_idx in range(0, n, 1):
        # Only start at sentence-beginning segments
        start_seg = segments[start_idx]
        if not _is_sentence_start(start_seg.get("text", "")):
            continue

        for end_idx in range(start_idx, n):
            end_seg = segments[end_idx]
            start_time = start_seg["start"]
            end_time = end_seg["end"]
            duration = end_time - start_time

            # Skip if too short
            if duration < lower_bound:
                continue

            # Stop if too long
            if duration > upper_bound:
                break

            # Must end at a sentence boundary, OR be the final segment of the video
            if not _is_sentence_end(end_seg.get("text", "")):
                is_last_segment = (end_idx == n - 1)
                next_duration = (
                    segments[end_idx + 1]["end"] - start_time
                    if end_idx + 1 < n
                    else duration
                )
                if is_last_segment or next_duration > upper_bound:
                    # Accept this as the boundary
                    pass
                else:
                    continue

            # Validate against video duration
            if video_duration > 0 and end_time > video_duration + 0.5:
                continue

            candidate_segs = segments[start_idx : end_idx + 1]
            text = " ".join(s.get("text", "").strip() for s in candidate_segs)

            candidate = ClipCandidate(
                start_time=round(start_time, 3),
                end_time=round(end_time, 3),
                duration=round(duration, 3),
                text=text,
                segments=candidate_segs,
                segment_indices=list(range(start_idx, end_idx + 1)),
            )
            candidates.append(candidate)

    # Fallback 1: If no candidates with strict sentence start, relax sentence boundaries
    if not candidates:
        logger.info("No candidates found with strict sentence boundaries; trying relaxed window matching")
        for start_idx in range(0, n):
            start_seg = segments[start_idx]
            for end_idx in range(start_idx, n):
                end_seg = segments[end_idx]
                start_time = start_seg["start"]
                end_time = end_seg["end"]
                duration = end_time - start_time

                if duration < lower_bound:
                    continue
                if duration > upper_bound and duration > min_duration:
                    break

                if video_duration > 0 and end_time > video_duration + 0.5:
                    continue

                candidate_segs = segments[start_idx : end_idx + 1]
                text = " ".join(s.get("text", "").strip() for s in candidate_segs)
                candidates.append(
                    ClipCandidate(
                        start_time=round(start_time, 3),
                        end_time=round(end_time, 3),
                        duration=round(duration, 3),
                        text=text,
                        segments=candidate_segs,
                        segment_indices=list(range(start_idx, end_idx + 1)),
                    )
                )

    # Fallback 2: If still empty (e.g. short video or sparse segments), use entire speech range
    if not candidates and segments:
        total_start = segments[0]["start"]
        total_end = segments[-1]["end"]
        total_dur = total_end - total_start
        if total_dur >= 3.0:
            logger.info("Using full available transcript range as fallback candidate", duration=total_dur)
            full_text = " ".join(s.get("text", "").strip() for s in segments)
            candidates.append(
                ClipCandidate(
                    start_time=round(total_start, 3),
                    end_time=round(total_end, 3),
                    duration=round(total_dur, 3),
                    text=full_text,
                    segments=segments,
                    segment_indices=list(range(len(segments))),
                )
            )

    # Deduplicate overlapping candidates — keep best duration match
    candidates = _deduplicate(candidates, target_duration)

    logger.info(
        "Candidates generated",
        total=len(candidates),
        target_duration=target_duration,
    )
    return candidates


def _is_sentence_start(text: str) -> bool:
    """Check if text likely starts a new sentence."""
    if not text:
        return False
    text = text.strip()
    if not text:
        return False
    # Starts with capital letter, or follows typical sentence starters
    return text[0].isupper() or text[0].isdigit()


def _is_sentence_end(text: str) -> bool:
    """Check if text likely ends a sentence."""
    if not text:
        return False
    text = text.strip()
    if not text:
        return False
    return text[-1] in ".!?;:" or len(text.split()) < 3


def _deduplicate(
    candidates: List[ClipCandidate],
    target_duration: int,
) -> List[ClipCandidate]:
    """
    Remove heavily overlapping candidates.
    When two candidates overlap by >70% of the shorter one, keep the one
    whose duration is closer to the target.
    """
    if len(candidates) <= 1:
        return candidates

    # Sort by start time
    candidates.sort(key=lambda c: c.start_time)
    kept: List[ClipCandidate] = []

    for cand in candidates:
        overlaps = False
        for existing in kept:
            overlap = _overlap_ratio(cand, existing)
            if overlap > 0.70:
                # Keep the one closer to target duration
                cand_diff = abs(cand.duration - target_duration)
                exist_diff = abs(existing.duration - target_duration)
                if cand_diff < exist_diff:
                    kept.remove(existing)
                    kept.append(cand)
                overlaps = True
                break
        if not overlaps:
            kept.append(cand)

    return kept


def _overlap_ratio(a: ClipCandidate, b: ClipCandidate) -> float:
    """Calculate overlap as fraction of the shorter clip's duration."""
    overlap_start = max(a.start_time, b.start_time)
    overlap_end = min(a.end_time, b.end_time)
    if overlap_end <= overlap_start:
        return 0.0
    overlap_duration = overlap_end - overlap_start
    shorter_duration = min(a.duration, b.duration)
    return overlap_duration / shorter_duration if shorter_duration > 0 else 0.0
