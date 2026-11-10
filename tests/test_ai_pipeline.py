"""
Unit tests for AI Pipeline: Prompt Parser, Candidate Generator, Subtitle Generator, Scorer.
"""
import sys
import os
import tempfile
import pytest

sys.path.insert(0, "/home/kalpesh/clipped-ai/backend")

from app.ai.understanding.prompt_parser import parse_prompt, PromptIntent
from app.ai.clip_selection.candidate_generator import generate_candidates, ClipCandidate
from app.ai.clip_selection.scorer import score_candidates
from app.video.captions.subtitle_generator import generate_srt, generate_ass


def test_prompt_parser_heuristic():
    prompt = "Find the most interesting part where the speaker discusses artificial intelligence replacing jobs. Make it engaging, approximately 30 seconds."
    intent = parse_prompt(prompt)
    assert intent.target_duration_seconds == 30
    assert any("intelligence" in kw.lower() or "artificial" in kw.lower() or "jobs" in kw.lower() for kw in intent.keywords)
    assert intent.tone in ("engaging", "educational", "informative")


def test_candidate_generation():
    # Mock transcript segments
    mock_segments = [
        {"id": 0, "start": 0.0, "end": 4.5, "text": "Hello and welcome to the show.", "avg_logprob": -0.2},
        {"id": 1, "start": 4.5, "end": 10.0, "text": "Today we are discussing the future of AI.", "avg_logprob": -0.15},
        {"id": 2, "start": 10.0, "end": 18.0, "text": "Will artificial intelligence take our jobs in tech?", "avg_logprob": -0.1},
        {"id": 3, "start": 18.0, "end": 28.0, "text": "Many software engineers are wondering about automation.", "avg_logprob": -0.12},
        {"id": 4, "start": 28.0, "end": 38.0, "text": "The reality is that tools like Claude and Gemini will transform work.", "avg_logprob": -0.18},
        {"id": 5, "start": 38.0, "end": 48.0, "text": "Rather than replacing developers, they elevate productivity exponentially.", "avg_logprob": -0.1},
        {"id": 6, "start": 48.0, "end": 55.0, "text": "That concludes our segment for today.", "avg_logprob": -0.25},
    ]

    candidates = generate_candidates(
        segments=mock_segments,
        target_duration=30,
        video_duration=60.0,
        min_duration=10,
        max_duration=45,
    )

    assert len(candidates) > 0
    for cand in candidates:
        assert cand.duration >= 10
        assert cand.duration <= 45
        assert len(cand.segments) > 0


def test_clip_scoring():
    mock_segments = [
        {"id": 1, "start": 4.5, "end": 10.0, "text": "Today we are discussing the future of AI.", "avg_logprob": -0.15},
        {"id": 2, "start": 10.0, "end": 18.0, "text": "Will artificial intelligence take our jobs in tech?", "avg_logprob": -0.1},
        {"id": 3, "start": 18.0, "end": 28.0, "text": "Many software engineers are wondering about automation.", "avg_logprob": -0.12},
        {"id": 4, "start": 28.0, "end": 35.0, "text": "The reality is that AI tools will transform how we code.", "avg_logprob": -0.18},
    ]

    cand = ClipCandidate(
        start_time=4.5,
        end_time=35.0,
        duration=30.5,
        text="Today we are discussing the future of AI. Will artificial intelligence take our jobs in tech? Many software engineers are wondering about automation. The reality is that AI tools will transform how we code.",
        segments=mock_segments,
        segment_indices=[1, 2, 3, 4],
    )

    intent = PromptIntent(
        topic="artificial intelligence and jobs",
        keywords=["artificial", "intelligence", "jobs", "automation"],
        target_duration_seconds=30,
        tone="engaging",
        content_type="highlight",
        reasoning="Test intent",
    )

    scored = score_candidates([cand], intent, video_duration=60.0, use_gemini_rerank=False)
    assert len(scored) == 1
    assert scored[0].score > 0.5
    assert scored[0].score_breakdown["relevance"] > 0.5
    assert scored[0].score_breakdown["hook_strength"] > 0.0


def test_subtitle_generation():
    segments = [
        {"start": 10.0, "end": 15.0, "text": "First caption line."},
        {"start": 15.0, "end": 20.0, "text": "Second caption line."},
    ]

    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as f:
        srt_path = f.name
    with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as f:
        ass_path = f.name

    try:
        generate_srt(segments, srt_path, start_offset=10.0)
        assert os.path.exists(srt_path)
        with open(srt_path, "r") as f:
            content = f.read()
            assert "00:00:00,000 --> 00:00:05,000" in content
            assert "First caption line." in content

        generate_ass(segments, ass_path, start_offset=10.0)
        assert os.path.exists(ass_path)
        with open(ass_path, "r") as f:
            content = f.read()
            assert "[Script Info]" in content
            assert "[V4+ Styles]" in content
            assert "First caption line." in content
    finally:
        if os.path.exists(srt_path):
            os.remove(srt_path)
        if os.path.exists(ass_path):
            os.remove(ass_path)
