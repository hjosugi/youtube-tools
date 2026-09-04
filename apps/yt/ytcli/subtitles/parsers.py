from __future__ import annotations

import re
from pathlib import Path

from ..models import AppError, SubtitleCue
from ..utils import clean_subtitle_text, normalize_timestamp

SRT_TIME_RE = re.compile(
    r"^(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})"
)
VTT_TIME_RE = re.compile(
    r"^(?P<start>(?:\d{1,2}:)?\d{2}:\d{2}\.\d{1,3})\s*-->\s*(?P<end>(?:\d{1,2}:)?\d{2}:\d{2}\.\d{1,3})"
)
VTT_SKIP_PREFIXES = ("NOTE", "STYLE", "REGION", "WEBVTT", "Kind:", "Language:")


def parse_srt(path: Path) -> list[SubtitleCue]:
    content = path.read_text(encoding="utf-8-sig", errors="replace")
    cues: list[SubtitleCue] = []
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines and lines[0].isdigit():
            lines = lines[1:]
        if len(lines) < 2:
            continue
        match = SRT_TIME_RE.match(lines[0])
        if not match:
            continue
        text = clean_subtitle_text(" ".join(lines[1:]))
        if text:
            cues.append(
                SubtitleCue(
                    start=normalize_timestamp(match.group("start")),
                    end=normalize_timestamp(match.group("end")),
                    text=text,
                )
            )
    return dedupe(cues)


def parse_vtt(path: Path) -> list[SubtitleCue]:
    cues: list[SubtitleCue] = []
    start = end = ""
    buffer: list[str] = []

    def flush() -> None:
        nonlocal start, end, buffer
        if start and end:
            text = clean_subtitle_text(" ".join(buffer))
            if text:
                cues.append(SubtitleCue(start=start, end=end, text=text))
        start = end = ""
        buffer = []

    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip().lstrip("﻿")
        if not line:
            flush()
            continue
        if line.startswith(VTT_SKIP_PREFIXES):
            continue
        match = VTT_TIME_RE.match(line)
        if match:
            flush()
            start = normalize_timestamp(match.group("start"))
            end = normalize_timestamp(match.group("end"))
            continue
        if not start:
            continue
        buffer.append(line)

    flush()
    return dedupe(cues)


def dedupe(cues: list[SubtitleCue]) -> list[SubtitleCue]:
    """YouTube auto-captions repeat the previous line while scrolling. Drop exact repeats."""
    result: list[SubtitleCue] = []
    for cue in cues:
        if result and result[-1].text == cue.text:
            previous = result[-1]
            result[-1] = SubtitleCue(start=previous.start, end=cue.end, text=cue.text)
            continue
        result.append(cue)
    return result


def parse_subtitle_file(path: Path) -> list[SubtitleCue]:
    suffix = path.suffix.lower()
    if suffix == ".srt":
        cues = parse_srt(path)
    elif suffix in (".vtt", ".webvtt"):
        cues = parse_vtt(path)
    else:
        raise AppError(f"Unsupported subtitle format: {path.suffix}")
    if not cues:
        raise AppError(f"Subtitle file had no readable lines: {path.name}")
    return cues
