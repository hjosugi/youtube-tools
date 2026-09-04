from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..models import DownloadCancelled, DownloadResult
from ..settings import Options
from .client import Cancelled, Logger, YdlLogger, progress_hook


@dataclass
class Job:
    """Everything one URL's download needs, so each stage takes a single argument."""

    options: Options
    url: str
    staging: Path
    result: DownloadResult
    log: Logger
    cancelled: Cancelled | None = None

    def warn(self, message: str) -> None:
        """Record a non-fatal problem and show it to the user."""
        self.result.warnings.append(message)
        self.log(f"  {message}")

    def save(self, target: Path, note: str = "") -> None:
        """Register a finished file so the caller can report it."""
        self.result.files.append(target)
        self.log(f"  saved {target.name}{note}")

    def stage_dir(self, name: str) -> Path:
        """Give each stage its own directory so its output is found by location, not by mtime."""
        path = self.staging / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def check_cancelled(self) -> None:
        """Stop between stages when the GUI asked to."""
        if self.cancelled is not None and self.cancelled():
            raise DownloadCancelled("stopped by the user")

    def ydl_options(self, out_dir: Path) -> dict:
        """The yt-dlp options every stage shares."""
        return {
            "outtmpl": str(out_dir / "%(title)s [%(id)s].%(ext)s"),
            "ignoreconfig": True,
            "updatetime": False,
            "quiet": True,
            "noprogress": True,
            "consoletitle": False,
            "logger": YdlLogger(self.log),
            "progress_hooks": [progress_hook(self.log, self.cancelled)],
            "nocheckcertificate": self.options.insecure,
            "retries": 3,
            "fragment_retries": 3,
        }
