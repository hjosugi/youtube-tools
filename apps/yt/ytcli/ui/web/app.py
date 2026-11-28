"""What the web UI's request handlers share: the settings, the queue and who is watching."""

from __future__ import annotations

import secrets
import threading
import time
from dataclasses import replace
from pathlib import Path

from ... import __version__, ffmpeg
from ...models import AUDIO_FORMATS, AUDIO_QUALITIES, VIDEO_FORMATS, VIDEO_QUALITIES, AppError
from ...settings import DEFAULTS, Options, config_path, save_config
from ...subtitles import SUBTITLE_FORMATS
from . import system
from .jobs import JobManager, UiJob


class App:
    """The state behind the page. Nothing in here knows about HTTP."""

    def __init__(
        self,
        options: Options,
        token: str | None = None,
        manager: JobManager | None = None,
        linger: float | None = None,
    ) -> None:
        # Exactly what the config file holds; see `current` for what downloads use.
        self.options = options
        self.token = token or secrets.token_urlsafe(24)
        self.manager = manager or JobManager()
        self.linger = linger
        self.stop = threading.Event()
        self._lock = threading.Lock()
        self._tabs = 0
        self._last_seen = time.monotonic()

    # ---- who is watching -------------------------------------------------------------

    @property
    def tabs_open(self) -> int:
        with self._lock:
            return self._tabs

    def tab_opened(self) -> None:
        with self._lock:
            self._tabs += 1

    def tab_closed(self) -> None:
        with self._lock:
            self._tabs -= 1
            self._last_seen = time.monotonic()

    def abandoned(self) -> bool:
        """True once no tab has been open for `linger` seconds and nothing is downloading."""
        if self.linger is None:
            return False
        with self._lock:
            if self._tabs or self.manager.active():
                self._last_seen = time.monotonic()
                return False
            return time.monotonic() - self._last_seen > self.linger

    # ---- settings --------------------------------------------------------------------

    @property
    def current(self) -> Options:
        """The settings to act on.

        A window has no "current directory", so a folder that was never chosen means
        Downloads here. The stored options keep the unset value, which leaves the command
        line's own default (the directory it is run in) alone.
        """
        options = self.options
        if options.output == DEFAULTS["output"]:
            return replace(options, output=str(system.downloads_dir()))
        return options

    def state(self) -> dict:
        """What the page needs to draw itself from scratch."""
        _revision, jobs = self.manager.snapshot()
        current = self.current
        folder = current.out_dir
        return {
            "version": __version__,
            "options": current.to_config(),
            "folder": str(folder),
            "folder_label": system.short_path(folder),
            "choices": {
                "video_quality": VIDEO_QUALITIES,
                "video_format": VIDEO_FORMATS,
                "audio_quality": AUDIO_QUALITIES,
                "audio_format": AUDIO_FORMATS,
                "sub_formats": SUBTITLE_FORMATS,
            },
            "ffmpeg": ffmpeg.status(),
            "first_run": not config_path().is_file(),
            "jobs": jobs,
        }

    def update_options(self, changes: dict) -> None:
        """Apply settings sent by the page and remember them as the new defaults."""
        values = {}
        for key, value in changes.items():
            if key not in DEFAULTS:
                continue
            if isinstance(DEFAULTS[key], bool):
                if not isinstance(value, bool):
                    raise AppError(f"{key} must be true or false.")
                values[key] = value
            elif isinstance(value, list | tuple):
                values[key] = ",".join(str(item) for item in value)
            elif isinstance(value, str):
                values[key] = value.strip()
            else:
                raise AppError(f"{key} must be text.")
        if values.get("output") == "":
            raise AppError("Choose a folder to save to.")
        if values.get("output") == ".":
            # An explicitly chosen working directory must survive restarting the UI.
            values["output"] = str(Path.cwd())
        self._remember(values)

    def submit(self, urls: list[str], mode: str) -> list[UiJob]:
        """Queue the URLs. The button pressed becomes the default, so Enter repeats it."""
        options = self._remember({"mode": mode} if mode else {})
        return self.manager.submit(urls, options)

    def _remember(self, changes: dict) -> Options:
        # Multiple tabs can change settings or queue jobs at the same time.
        with self._lock:
            updated = Options.from_config(self.options.to_config() | changes)
            updated.insecure = self.options.insecure
            save_config(updated.to_config())
            self.options = updated
            return self.current
