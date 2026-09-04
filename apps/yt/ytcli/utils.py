from __future__ import annotations

import re
from pathlib import Path

YOUTUBE_ID_SUFFIX_RE = re.compile(r"\s*\[[A-Za-z0-9_-]{11}\]$")
TAG_RE = re.compile(r"<[^>]+>")
MAX_STEM_LENGTH = 120


def split_list(value: str) -> tuple[str, ...]:
    """Split a comma or space separated option value into clean parts."""
    parts = [part.strip() for part in re.split(r"[,\s]+", value or "") if part.strip()]
    seen: list[str] = []
    for part in parts:
        if part not in seen:
            seen.append(part)
    return tuple(seen)


def _looks_like_extension(candidate: str) -> bool:
    """True for 'mp4' or 'srt', false for '0' so 'Talk 2.0' keeps its name."""
    return (
        0 < len(candidate) <= 12
        and candidate.replace("-", "").isalnum()
        and any(char.isalpha() for char in candidate)
    )


def base_stem(path: Path, language: str = "") -> str:
    """Turn 'Some Title [dQw4w9WgXcQ].en.srt' into 'Some Title'."""
    name = path.name
    stem, dot, extension = name.rpartition(".")
    if dot and _looks_like_extension(extension):
        name = stem
    if language and name.endswith(f".{language}"):
        name = name[: -(len(language) + 1)]
    name = YOUTUBE_ID_SUFFIX_RE.sub("", name).strip()
    if len(name) > MAX_STEM_LENGTH:
        name = name[:MAX_STEM_LENGTH].rstrip()
    return name or "video"


def language_of(path: Path) -> str:
    """Read the language tag yt-dlp puts before the extension, if any."""
    parts = path.name.split(".")
    if len(parts) < 3:
        return ""
    candidate = parts[-2]
    if re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*", candidate):
        return candidate
    return ""


def clean_subtitle_text(text: str) -> str:
    return " ".join(TAG_RE.sub("", text).split())


def normalize_timestamp(timestamp: str) -> str:
    """Normalise to HH:MM:SS.mmm regardless of comma or missing hour part."""
    value = timestamp.strip().replace(",", ".")
    head, _, millis = value.partition(".")
    pieces = head.split(":")
    while len(pieces) < 3:
        pieces.insert(0, "00")
    hours, minutes, seconds = (piece.zfill(2) for piece in pieces[-3:])
    return f"{hours}:{minutes}:{seconds}.{(millis or '000')[:3].ljust(3, '0')}"


def srt_timestamp(timestamp: str) -> str:
    return normalize_timestamp(timestamp).replace(".", ",")


def unique_path(path: Path) -> Path:
    """Avoid clobbering an existing file by adding ' (2)', ' (3)' and so on."""
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise OSError(f"Could not find a free filename for {path}")
