"""
SRT/ASS Subtitle Generator
Creates subtitle files from timestamped transcript segments.
"""
from __future__ import annotations

import os
from typing import List


def seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def seconds_to_ass_time(seconds: float) -> str:
    """Convert seconds to ASS time format: H:MM:SS.cs"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


def generate_srt(
    segments: List[dict],
    output_path: str,
    start_offset: float = 0.0,
) -> str:
    """
    Generate an SRT subtitle file from transcript segments.

    Args:
        segments: List of {start, end, text} dicts
        output_path: Where to write the .srt file
        start_offset: Subtract this from all timestamps (for trimmed clips)

    Returns:
        Path to the created .srt file
    """
    lines = []
    entry_num = 1

    for seg in segments:
        start = max(0.0, seg["start"] - start_offset)
        end = max(0.0, seg["end"] - start_offset)
        text = seg.get("text", "").strip()

        if not text or end <= start:
            continue

        lines.append(str(entry_num))
        lines.append(f"{seconds_to_srt_time(start)} --> {seconds_to_srt_time(end)}")
        lines.append(text)
        lines.append("")
        entry_num += 1

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


def generate_ass(
    segments: List[dict],
    output_path: str,
    start_offset: float = 0.0,
    font_name: str = "Arial",
    font_size: int = 24,
    primary_color: str = "&H00FFFFFF",   # white
    outline_color: str = "&H00000000",   # black
    bold: bool = True,
    outline_width: float = 2.0,
    shadow: float = 1.5,
    alignment: int = 2,                  # 2=bottom center, 5=middle center, 8=top center
    margin_v: int = 40,
) -> str:
    """
    Generate an ASS subtitle file with styled captions.
    ASS format allows richer styling than SRT.

    Returns:
        Path to the created .ass file
    """
    bold_flag = -1 if bold else 0

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},&H000000FF,{outline_color},&H80000000,{bold_flag},0,0,0,100,100,0,0,1,{outline_width},{shadow},{alignment},20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_lines = []
    for seg in segments:
        start = max(0.0, seg["start"] - start_offset)
        end = max(0.0, seg["end"] - start_offset)
        text = seg.get("text", "").strip()

        if not text or end <= start:
            continue

        # Escape braces in text
        text = text.replace("{", "\\{").replace("}", "\\}")

        dialogue_lines.append(
            f"Dialogue: 0,{seconds_to_ass_time(start)},{seconds_to_ass_time(end)},Default,,0,0,0,,{text}"
        )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n".join(dialogue_lines))

    return output_path
