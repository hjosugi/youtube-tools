from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path

from ..models import SubtitleCue
from ..utils import srt_timestamp


def write_srt(cues: list[SubtitleCue], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for index, cue in enumerate(cues, start=1):
            handle.write(f"{index}\n")
            handle.write(f"{srt_timestamp(cue.start)} --> {srt_timestamp(cue.end)}\n")
            handle.write(f"{cue.text}\n\n")


def write_vtt(cues: list[SubtitleCue], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("WEBVTT\n\n")
        for cue in cues:
            handle.write(f"{cue.time_range}\n")
            handle.write(f"{cue.text}\n\n")


def write_tsv(cues: list[SubtitleCue], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["no", "start", "end", "text"])
        for index, cue in enumerate(cues, start=1):
            writer.writerow([index, cue.start, cue.end, cue.text])


def write_txt(cues: list[SubtitleCue], path: Path) -> None:
    path.write_text("\n".join(cue.text for cue in cues) + "\n", encoding="utf-8")


def write_md(cues: list[SubtitleCue], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"# {path.stem}\n\n")
        for index, cue in enumerate(cues, start=1):
            handle.write(f"## {index}\n\n")
            handle.write(f"`{cue.time_range}`\n\n")
            handle.write(f"{cue.text}\n\n")


SUBTITLE_WRITERS: dict[str, Callable[[list[SubtitleCue], Path], None]] = {
    "srt": write_srt,
    "vtt": write_vtt,
    "tsv": write_tsv,
    "txt": write_txt,
    "md": write_md,
}

SUBTITLE_FORMATS: tuple[str, ...] = tuple(SUBTITLE_WRITERS)
