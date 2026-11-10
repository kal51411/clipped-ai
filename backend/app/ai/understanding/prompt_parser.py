"""
Gemini Prompt Understanding Service
Parses a user's natural language prompt into a structured PromptIntent.
Uses google-genai interactions API with structured output (JSON schema).
"""
from __future__ import annotations

import json
from typing import List, Optional

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import AIServiceError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


# ── Structured output schema ──────────────────────────────────────────────────
class PromptIntent(BaseModel):
    """Parsed intent extracted from a user's natural language clip request."""
    topic: str = Field(description="The main topic or subject the user wants")
    keywords: List[str] = Field(description="Important keywords from the prompt")
    target_duration_seconds: Optional[int] = Field(
        default=60,
        description="Desired clip duration in seconds (10-180)",
    )
    tone: str = Field(
        default="engaging",
        description="Desired tone: educational, entertaining, dramatic, informative, inspiring",
    )
    hook_preference: Optional[str] = Field(
        default=None,
        description="Preferred hook style: question, statement, surprising_fact, action",
    )
    content_type: str = Field(
        default="highlight",
        description="highlight | quote | story | explanation | debate | moment",
    )
    avoid_keywords: List[str] = Field(
        default_factory=list,
        description="Topics or keywords to avoid",
    )
    reasoning: str = Field(
        description="Brief explanation of how you interpreted the prompt",
    )


_SYSTEM_PROMPT = """You are a video content intelligence assistant.
Your job is to parse user prompts about video clip generation into structured JSON.

Rules:
- Extract the core topic and keywords
- Infer target duration if mentioned (default 60s, range 10-180s)
- Identify tone (educational/entertaining/dramatic/informative/inspiring)
- Identify content type (highlight/quote/story/explanation/debate/moment)
- If the user says "30 seconds", set target_duration_seconds to 30
- Keywords should be specific and searchable in a transcript
- reasoning should be 1-2 concise sentences

Always respond with valid JSON matching the schema exactly.
"""

_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "target_duration_seconds": {"type": "integer", "minimum": 10, "maximum": 180},
        "tone": {"type": "string"},
        "hook_preference": {"type": ["string", "null"]},
        "content_type": {"type": "string"},
        "avoid_keywords": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["topic", "keywords", "tone", "content_type", "reasoning"],
}


def parse_prompt(user_prompt: str) -> PromptIntent:
    """
    Use Gemini to parse a natural language prompt into a PromptIntent.
    Falls back to a simple keyword-extraction heuristic if Gemini is unavailable.
    """
    if not settings.GEMINI_ENABLED:
        logger.warning(
            "GEMINI_API_KEY not configured — using heuristic prompt parser"
        )
        return _heuristic_parse(user_prompt)

    try:
        from google import genai
        import re

        client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options={"api_version": "v1beta"},
        )

        prompt_text = f"""You are an expert AI video clipping editor. Parse the following clip request into valid JSON.
Fields required:
- topic: string (the core topic)
- keywords: array of strings (searchable keywords for matching transcripts)
- target_duration_seconds: integer (desired duration, default 30-60, between 10 and 180)
- tone: string (e.g. funny, viral, educational, inspiring, intense)
- content_type: string (highlight, quote, story, explanation, moment)
- reasoning: string (brief explanation of interpretation)

User request: "{user_prompt}"

Return ONLY valid JSON:"""

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt_text,
            config={"response_mime_type": "application/json"},
        )

        raw = (response.text or "").strip()
        # Clean markdown codeblocks if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        data = json.loads(raw)
        if isinstance(data.get("keywords"), str):
            data["keywords"] = [k.strip() for k in data["keywords"].split(",") if k.strip()]

        intent = PromptIntent(
            topic=data.get("topic", user_prompt[:40]),
            keywords=data.get("keywords") or [word for word in user_prompt.split() if len(word) > 3],
            target_duration_seconds=data.get("target_duration_seconds") or 30,
            tone=data.get("tone", "engaging"),
            content_type=data.get("content_type", "highlight"),
            reasoning=data.get("reasoning", "Parsed with Gemini"),
        )

        # Clamp duration
        if intent.target_duration_seconds:
            intent.target_duration_seconds = max(
                settings.MIN_CLIP_DURATION_SECONDS,
                min(settings.MAX_CLIP_DURATION_SECONDS, intent.target_duration_seconds),
            )

        logger.info(
            "Prompt parsed by Gemini",
            topic=intent.topic,
            keywords=intent.keywords,
            duration=intent.target_duration_seconds,
        )
        return intent

    except Exception as e:
        logger.error("Gemini prompt parsing failed, falling back to heuristic", error=str(e))
        return _heuristic_parse(user_prompt)


def _heuristic_parse(prompt: str) -> PromptIntent:
    """
    Simple heuristic fallback when Gemini is not available.
    Extracts keywords from the prompt text.
    """
    import re

    # Extract duration hints
    duration = settings.DEFAULT_CLIP_DURATION_SECONDS
    patterns = [
        r"(\d+)\s*second", r"(\d+)\s*sec", r"(\d+)s\b",
        r"(\d+)\s*minute", r"(\d+)\s*min",
    ]
    for pat in patterns:
        m = re.search(pat, prompt, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if "minute" in pat or "min" in pat:
                val *= 60
            duration = max(10, min(180, val))
            break

    # Extract keywords: nouns and meaningful words
    stop_words = {
        "find", "the", "a", "an", "make", "it", "engaging", "approximately",
        "about", "where", "with", "and", "or", "in", "of", "to", "for",
        "is", "are", "was", "were", "be", "been", "have", "has", "had",
        "do", "does", "did", "will", "would", "could", "should", "most",
        "interesting", "part", "that", "this", "which", "who", "what",
    }
    words = re.findall(r"\b[a-zA-Z]{3,}\b", prompt)
    keywords = list(dict.fromkeys(
        w.lower() for w in words if w.lower() not in stop_words
    ))[:10]

    # Detect tone
    tone = "engaging"
    tone_map = {
        "educational": ["explain", "learn", "teach", "understand", "how", "why"],
        "entertaining": ["funny", "humor", "laugh", "entertain", "fun"],
        "dramatic": ["dramatic", "intense", "emotional", "shocking"],
        "informative": ["inform", "fact", "news", "stat", "data"],
        "inspiring": ["inspire", "motivat", "success", "achiev"],
    }
    prompt_lower = prompt.lower()
    for t, signals in tone_map.items():
        if any(s in prompt_lower for s in signals):
            tone = t
            break

    return PromptIntent(
        topic=" ".join(keywords[:3]) if keywords else prompt[:50],
        keywords=keywords,
        target_duration_seconds=duration,
        tone=tone,
        content_type="highlight",
        reasoning=f"Heuristic parse: extracted {len(keywords)} keywords from prompt",
    )
