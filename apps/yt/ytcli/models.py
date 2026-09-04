from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Choice lists shared by the CLI flags, the GUI dropdowns and the config file.
VIDEO_QUALITIES = ("best", "2160", "1440", "1080", "720", "480", "360", "worst")
AUDIO_QUALITIES = ("best", "320", "256", "192", "128", "96", "64")
VIDEO_FORMATS = ("mp4", "mkv", "webm")
AUDIO_FORMATS = ("mp3", "m4a", "opus", "flac", "wav")


class AppError(RuntimeError):
    """Any failure that should be reported to the user without a traceback."""


class DownloadCancelled(AppError):
    """Raised when the user stops a running download."""


@dataclass(frozen=True)
class SubtitleCue:
    start: str
    end: str
    text: str

    @property
    def time_range(self) -> str:
        return f"{self.start} --> {self.end}"


@dataclass(frozen=True)
class SubtitleTracks:
    """The subtitle languages a video actually offers."""

    manual: tuple[str, ...] = ()
    automatic: tuple[str, ...] = ()


@dataclass
class DownloadResult:
    url: str
    files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
