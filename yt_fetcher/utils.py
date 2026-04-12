import subprocess
import re
from pathlib import Path

def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)

def base_stem(path: Path) -> str:
    # Keep the root name stripping out all extensions like .en.srt
    return path.name.split('.')[0]

def clean_subtitle_text(text: str) -> str:
    # Remove formatting tags like <i>, <b>, <font>
    cleaned = re.sub(r"<[^>]+>", "", text)
    # Collapse multiple spaces and newlines
    return " ".join(cleaned.split())

def normalize_timestamp(ts: str) -> str:
    # Force decimal instead of comma for milliseconds
    return ts.replace(",", ".")
