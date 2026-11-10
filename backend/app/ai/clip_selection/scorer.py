"""
Clip Scoring System
Deterministic multi-factor scoring with optional Gemini re-ranking.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import List, Optional

from app.ai.clip_selection.candidate_generator import ClipCandidate
from app.ai.understanding.prompt_parser import PromptIntent
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ScoredClip:
    candidate: ClipCandidate
    score: float
    score_breakdown: dict
    rank: int = 0
    gemini_reasoning: Optional[str] = None


def score_candidates(
    candidates: List[ClipCandidate],
    intent: PromptIntent,
    video_duration: float = 0.0,
    use_gemini_rerank: bool = True,
) -> List[ScoredClip]:
    """
    Score all candidates using deterministic metrics, then optionally
    re-rank top candidates with Gemini.

    Returns candidates sorted by score descending.
    """
    if not candidates:
        return []

    scored: List[ScoredClip] = []
    for cand in candidates:
        breakdown = _compute_scores(cand, intent, video_duration)
        total = _weighted_total(breakdown)
        scored.append(ScoredClip(candidate=cand, score=total, score_breakdown=breakdown))

    # Sort by deterministic score
    scored.sort(key=lambda s: s.score, reverse=True)

    # Gemini re-ranking on top 10 candidates (optional)
    if use_gemini_rerank and settings.GEMINI_ENABLED and len(scored) > 1:
        top_n = scored[: min(10, len(scored))]
        try:
            top_n = _gemini_rerank(top_n, intent)
            # Merge back
            scored[: len(top_n)] = top_n
        except Exception as e:
            logger.warning("Gemini reranking failed, using deterministic scores", error=str(e))

    # Assign ranks
    for i, s in enumerate(scored):
        s.rank = i + 1

    return scored


def _compute_scores(
    cand: ClipCandidate,
    intent: PromptIntent,
    video_duration: float,
) -> dict:
    """Compute individual scoring dimensions."""
    text = cand.text.lower()
    keywords = [kw.lower() for kw in intent.keywords]

    # 1. Keyword/topic relevance (0-1)
    if keywords:
        matched = sum(1 for kw in keywords if kw in text)
        relevance = matched / len(keywords)
        # Boost for exact multi-word phrase matches
        if intent.topic.lower() in text:
            relevance = min(1.0, relevance + 0.2)
    else:
        relevance = 0.5

    # 2. Hook strength — first sentence quality (0-1)
    first_sentence = _get_first_sentence(cand.text)
    hook_strength = _score_hook(first_sentence, intent)

    # 3. Context completeness — does it end naturally? (0-1)
    last_sentence = _get_last_sentence(cand.text)
    ends_naturally = cand.text.strip()[-1] in ".!?" if cand.text.strip() else False
    starts_naturally = cand.text.strip()[0].isupper() if cand.text.strip() else False
    context_completeness = (
        (0.4 if ends_naturally else 0.1)
        + (0.3 if starts_naturally else 0.0)
        + (0.3 if len(cand.segments) >= 3 else 0.1)
    )

    # 4. Duration match (0-1) — Gaussian around target
    target = intent.target_duration_seconds or 60
    duration_diff = abs(cand.duration - target)
    sigma = target * 0.3  # 30% tolerance standard deviation
    duration_score = math.exp(-(duration_diff**2) / (2 * sigma**2))

    # 5. Engagement potential — keyword density, question hooks (0-1)
    word_count = len(text.split())
    kw_density = (sum(text.count(kw) for kw in keywords) / word_count) if word_count > 0 else 0
    engagement = min(1.0, kw_density * 5 + 0.3)
    if "?" in cand.text:
        engagement = min(1.0, engagement + 0.2)
    if any(w in text for w in ["surprising", "shocking", "never", "always", "secret", "truth"]):
        engagement = min(1.0, engagement + 0.1)

    # 6. Speech clarity — penalize low avg_logprob (0-1)
    if cand.segments:
        avg_logprob = sum(
            s.get("avg_logprob", -0.5) for s in cand.segments
        ) / len(cand.segments)
        # avg_logprob is negative; closer to 0 = more confident
        clarity = max(0.0, min(1.0, 1.0 + avg_logprob * 2))
    else:
        clarity = 0.5

    return {
        "relevance": round(relevance, 4),
        "hook_strength": round(hook_strength, 4),
        "context_completeness": round(context_completeness, 4),
        "duration_match": round(duration_score, 4),
        "engagement_potential": round(engagement, 4),
        "speech_clarity": round(clarity, 4),
    }


def _weighted_total(breakdown: dict) -> float:
    """Weighted average of all score dimensions."""
    weights = {
        "relevance": 0.30,
        "hook_strength": 0.20,
        "context_completeness": 0.15,
        "duration_match": 0.15,
        "engagement_potential": 0.12,
        "speech_clarity": 0.08,
    }
    total = sum(breakdown.get(k, 0) * w for k, w in weights.items())
    return round(total, 4)


def _get_first_sentence(text: str) -> str:
    if not text:
        return ""
    match = re.match(r"[^.!?]+[.!?]?", text.strip())
    return match.group(0) if match else text[:100]


def _get_last_sentence(text: str) -> str:
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return sentences[-1] if sentences else text[-100:]


def _score_hook(sentence: str, intent: PromptIntent) -> float:
    """Score the hook quality of the opening sentence."""
    if not sentence:
        return 0.1
    score = 0.3  # base
    lower = sentence.lower()

    # Questions are great hooks
    if sentence.strip().endswith("?"):
        score += 0.3
    # Numbers / stats
    if re.search(r"\d+", sentence):
        score += 0.2
    # Action words
    action_words = ["think", "believe", "know", "imagine", "consider", "look", "listen"]
    if any(w in lower for w in action_words):
        score += 0.1
    # Short and punchy (under 15 words)
    if len(sentence.split()) <= 15:
        score += 0.1
    # Contains keywords
    if any(kw.lower() in lower for kw in intent.keywords):
        score += 0.1

    return min(1.0, score)


def _gemini_rerank(
    top_candidates: List[ScoredClip],
    intent: PromptIntent,
) -> List[ScoredClip]:
    """
    Use Gemini to re-rank the top candidates and provide reasoning.
    Only adjusts ranking — does not modify timestamps or text.
    """
    try:
        from google import genai

        client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options={"api_version": "v1beta"},
        )

        # Build prompt
        candidates_text = "\n\n".join(
            f"CANDIDATE {i + 1} (score={c.score:.3f}, duration={c.candidate.duration:.1f}s):\n{c.candidate.text[:500]}"
            for i, c in enumerate(top_candidates)
        )

        prompt = (
            f"You are a short-form video clip quality judge. Given candidate clips and a user's intent, "
            f"rank them from most to least engaging and viral.\n"
            f"User wants: {intent.topic}\n"
            f"Keywords: {', '.join(intent.keywords)}\n"
            f"Tone: {intent.tone}\n\n"
            f"Candidates:\n{candidates_text}\n\n"
            f"Return ONLY a JSON array of integers with candidate numbers in order of preference (e.g. [3, 1, 2])."
        )

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )

        raw = (response.text or "").strip()
        # Extract JSON array from response
        match = re.search(r"\[[\d,\s]+\]", raw)
        if not match:
            return top_candidates

        ranking = json.loads(match.group(0))

        # Reorder candidates based on Gemini's ranking
        reordered: List[ScoredClip] = []
        for rank_num in ranking:
            idx = rank_num - 1
            if 0 <= idx < len(top_candidates):
                reordered.append(top_candidates[idx])

        # Append any candidates Gemini didn't mention
        mentioned = set(r - 1 for r in ranking)
        for i, c in enumerate(top_candidates):
            if i not in mentioned:
                reordered.append(c)

        logger.info("Gemini reranking applied", order=ranking)
        return reordered

    except Exception as e:
        logger.warning("Gemini reranking failed, keeping deterministic scoring order", error=str(e))
        return top_candidates

