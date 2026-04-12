import re
from pathlib import Path


def base_stem(path: Path) -> str:
    name = path.name.split(".")[0]
    # Remove yt-dlp [YoutubeID] suffix if present
    name = re.sub(r"\s\[[a-zA-Z0-9_-]{21}\]$", "", name)
    # Truncate to 20 characters
    if len(name) > 20:
        name = name[:20]
    return name.strip()


def clean_subtitle_text(text: str) -> str:
    # Remove formatting tags like <i>, <b>, <font>
    cleaned = re.sub(r"<[^>]+>", "", text)
    # Collapse multiple spaces and newlines
    return " ".join(cleaned.split())


def normalize_timestamp(ts: str) -> str:
    # Force decimal instead of comma for milliseconds
    return ts.replace(",", ".")
