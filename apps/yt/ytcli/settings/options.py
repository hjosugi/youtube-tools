from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..models import (
    AUDIO_FORMATS,
    AUDIO_QUALITIES,
    VIDEO_FORMATS,
    VIDEO_QUALITIES,
    AppError,
)
from ..modes import parse_modes
from ..subtitles.writers import SUBTITLE_FORMATS
from ..utils import split_list
from .storage import load_config


@dataclass
class Options:
    """Effective settings after merging built-in defaults, the config file and the CLI."""

    urls: list[str] = field(default_factory=list)
    modes: str = "s"
    output: str = "."
    sub_langs: tuple[str, ...] = ("en",)
    sub_formats: tuple[str, ...] = ("srt", "tsv")
    auto_subs: bool = True
    video_quality: str = "best"
    video_format: str = "mp4"
    audio_quality: str = "best"
    audio_format: str = "mp3"
    insecure: bool = False

    @classmethod
    def load(cls) -> Options:
        """The user's saved defaults, or the built-in ones when there is no config file."""
        return cls.from_config(load_config(DEFAULTS))

    @classmethod
    def from_config(cls, config: dict[str, Any] | None = None) -> Options:
        """Build options from stored values, rejecting anything the tool cannot use."""
        values = DEFAULTS | dict(config or {})
        return cls(
            modes=parse_modes(str(values["mode"])),
            output=str(values["output"]),
            sub_langs=split_list(str(values["sub_langs"])) or ("en",),
            sub_formats=validate_sub_formats(split_list(str(values["sub_formats"]))),
            auto_subs=bool(values["auto_subs"]),
            video_quality=validate_choice("video_quality", values, VIDEO_QUALITIES),
            video_format=validate_choice("video_format", values, VIDEO_FORMATS),
            audio_quality=validate_choice("audio_quality", values, AUDIO_QUALITIES),
            audio_format=validate_choice("audio_format", values, AUDIO_FORMATS),
        )

    def to_config(self) -> dict[str, Any]:
        """The storable half of the settings; urls and --insecure are per-run, not defaults."""
        return {
            "output": self.output,
            "mode": self.modes,
            "sub_langs": ",".join(self.sub_langs),
            "sub_formats": ",".join(self.sub_formats),
            "auto_subs": self.auto_subs,
            "video_quality": self.video_quality,
            "video_format": self.video_format,
            "audio_quality": self.audio_quality,
            "audio_format": self.audio_format,
        }

    @property
    def out_dir(self) -> Path:
        """Where finished files go, with ~ expanded and made absolute."""
        return Path(self.output).expanduser().resolve()


def validate_choice(key: str, values: dict[str, Any], allowed: tuple[str, ...]) -> str:
    """Read one setting and fail loudly when a config file holds something unusable."""
    value = str(values[key])
    if value not in allowed:
        raise AppError(f"Invalid {key}: {value!r}. Choose from: {', '.join(allowed)}")
    return value


def validate_sub_formats(formats: tuple[str, ...]) -> tuple[str, ...]:
    """Keep only formats we have a writer for, defaulting to srt when none are given."""
    if not formats:
        return ("srt",)
    unknown = [item for item in formats if item not in SUBTITLE_FORMATS]
    if unknown:
        raise AppError(
            f"Unknown subtitle format(s): {', '.join(unknown)}. "
            f"Choose from: {', '.join(SUBTITLE_FORMATS)}"
        )
    return formats


# Single source of truth for the defaults: whatever a bare Options() holds.
DEFAULTS: dict[str, Any] = Options().to_config()
