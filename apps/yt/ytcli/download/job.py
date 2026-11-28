from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models import Cancelled, DownloadCancelled, DownloadResult, Logger, Notify, SubtitleTracks, silent
from ..settings import Options
from .client import base_options, progress_hook


@dataclass
class Job:
    """Everything one URL's download needs, so each stage takes a single argument."""

    options: Options
    url: str
    staging: Path
    result: DownloadResult
    log: Logger
    cancelled: Cancelled | None = None
    notify: Notify = silent
    # The subtitle languages of the video, when the caller has just looked them up.
    tracks: SubtitleTracks | None = None

    def tell(self, kind: str, **details) -> None:
        """Send a structured event to whoever is drawing progress."""
        self.notify(kind, details)

    def warn(self, message: str) -> None:
        """Record a non-fatal problem and show it to the user."""
        self.result.warnings.append(message)
        self.log(f"  {message}")
        self.tell("warning", message=message)

    def save(self, target: Path, note: str = "") -> None:
        """Register a finished file so the caller can report it."""
        self.result.files.append(target)
        self.log(f"  saved {target.name}{note}")
        self.tell("saved", path=str(target))

    def stage_dir(self, name: str) -> Path:
        """Give each stage its own directory so its output is found by location, not by mtime."""
        path = self.staging / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def check_cancelled(self) -> None:
        """Stop between stages when the user asked to."""
        if self.cancelled is not None and self.cancelled():
            raise DownloadCancelled("stopped by the user")

    def ydl_options(self, out_dir: Path, stage: str) -> dict:
        """The yt-dlp options every stage shares."""
        return base_options(self.log, self.options.insecure) | {
            "outtmpl": str(out_dir / "%(title)s [%(id)s].%(ext)s"),
            "updatetime": False,
            "progress_hooks": [progress_hook(self.log, self.cancelled, self.notify, stage)],
            "retries": 3,
            "fragment_retries": 3,
        }
