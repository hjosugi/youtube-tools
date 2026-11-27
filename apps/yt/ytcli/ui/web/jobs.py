"""The download queue behind the web UI: one worker thread and jobs the page can watch."""

from __future__ import annotations

import itertools
import queue
import shlex
import subprocess
import sys
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path

from ...download import download, is_playlist_url, probe
from ...models import AppError, DownloadCancelled, VideoInfo
from ...modes import ALL_MODES
from ...settings import DEFAULTS, Options

LOG_LINES = 400
INFO_CACHE_SIZE = 64
FINISHED = ("done", "failed", "cancelled")


@dataclass
class UiJob:
    """One URL being downloaded, in the shape the page draws it."""

    id: str
    url: str
    options: Options
    title: str = ""
    video_id: str = ""
    status: str = "queued"  # queued, running, done, failed or cancelled
    stage: str = ""  # subtitle, audio, video, ffmpeg or playlist
    percent: float | None = None
    processing: bool = False
    files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str = ""
    log: deque[str] = field(default_factory=lambda: deque(maxlen=LOG_LINES))
    log_count: int = 0
    stop: threading.Event = field(default_factory=threading.Event)

    @property
    def finished(self) -> bool:
        return self.status in FINISHED

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "video_id": self.video_id,
            "modes": self.options.modes,
            "audio_format": self.options.audio_format,
            "video_format": self.options.video_format,
            "status": self.status,
            "stage": self.stage,
            "percent": self.percent,
            "processing": self.processing,
            "files": [{"name": path.name, "size": _size(path)} for path in self.files],
            "folder": str(self.options.out_dir),
            "warnings": list(self.warnings),
            "error": self.error,
            "command": command_line(self.options, self.url),
            "log_count": self.log_count,
        }


class JobManager:
    """Queues downloads, runs them one at a time and tells waiting readers what changed."""

    def __init__(self, download_fn: Callable = download, probe_fn: Callable = probe) -> None:
        self._download = download_fn
        self._probe = probe_fn
        self._changed = threading.Condition()
        self._jobs: dict[str, UiJob] = {}
        self._pending: queue.Queue[UiJob | None] = queue.Queue()
        self._ids = itertools.count(1)
        self._revision = 0
        self._info: dict[str, VideoInfo] = {}
        self._worker = threading.Thread(target=self._work, daemon=True, name="yt-downloads")
        self._worker.start()

    # ---- what the HTTP handlers call -------------------------------------------------

    def info(self, url: str, insecure: bool = False) -> VideoInfo:
        """Look a URL up once and remember the answer for the job that follows."""
        with self._changed:
            cached = self._info.get(url)
        if cached is not None:
            return cached
        found = self._probe(url, insecure=insecure)
        with self._changed:
            self._info[url] = found
            while len(self._info) > INFO_CACHE_SIZE:
                self._info.pop(next(iter(self._info)))
        return found

    def submit(self, urls: list[str], options: Options) -> list[UiJob]:
        """Queue one job per URL, each with its own frozen copy of the options."""
        jobs = []
        with self._changed:
            for url in urls:
                job = UiJob(id=str(next(self._ids)), url=url, options=replace(options, urls=[url]))
                self._describe(job, self._info.get(url))
                self._jobs[job.id] = job
                jobs.append(job)
            self._bump()
        for job in jobs:
            self._pending.put(job)
        return jobs

    def cancel(self, job_id: str) -> bool:
        """Stop a job: at once when it is still queued, at the next checkpoint otherwise."""
        with self._changed:
            job = self._jobs.get(job_id)
            if job is None or job.finished:
                return False
            job.stop.set()
            if job.status == "queued":
                job.status = "cancelled"
            self._bump()
        return True

    def clear(self) -> None:
        """Forget every job that is no longer doing anything."""
        with self._changed:
            self._jobs = {job_id: job for job_id, job in self._jobs.items() if not job.finished}
            self._bump()

    def get(self, job_id: str) -> UiJob | None:
        with self._changed:
            return self._jobs.get(job_id)

    def log_lines(self, job_id: str) -> list[str] | None:
        with self._changed:
            job = self._jobs.get(job_id)
            return None if job is None else list(job.log)

    def snapshot(self) -> tuple[int, list[dict]]:
        """Every job as JSON, with the revision number it was taken at."""
        with self._changed:
            return self._revision, [job.to_json() for job in self._jobs.values()]

    def wait(self, revision: int, timeout: float) -> int:
        """Block until something changed since `revision`, or the timeout passed."""
        with self._changed:
            self._changed.wait_for(lambda: self._revision != revision, timeout)
            return self._revision

    def active(self) -> bool:
        with self._changed:
            return any(not job.finished for job in self._jobs.values())

    def shutdown(self, timeout: float = 5.0) -> None:
        """Stop everything and give the worker a moment to clean up its temp files."""
        with self._changed:
            for job in self._jobs.values():
                job.stop.set()
        self._pending.put(None)
        self._worker.join(timeout)

    # ---- the worker thread -----------------------------------------------------------

    def _work(self) -> None:
        while True:
            job = self._pending.get()
            if job is None:
                return
            if job.finished:  # cancelled while it was still waiting
                continue
            self._run(job)

    def _run(self, job: UiJob) -> None:
        self._set(job, status="running")
        try:
            if is_playlist_url(job.url):
                self._expand(job)
                return
            self._name(job)
            result = self._download(
                job.options,
                job.url,
                lambda line: self._log(job, line),
                job.stop.is_set,
                lambda kind, details: self._notify(job, kind, details),
            )
        except DownloadCancelled:
            self._set(job, status="cancelled")
        except AppError as error:
            self._set(job, status="failed", error=str(error))
        except Exception as error:  # yt-dlp and ffmpeg raise a wide range of errors
            self._set(job, status="failed", error=f"unexpected error: {error}")
        else:
            self._set(
                job, status="done", files=list(result.files), warnings=list(result.warnings), percent=100.0
            )

    def _expand(self, job: UiJob) -> None:
        """Replace a playlist job with one job per video."""
        self._set(job, stage="playlist")
        entries = self._probe(job.url, insecure=job.options.insecure).entries
        if not entries:
            raise AppError("This playlist has no videos.")
        with self._changed:
            self._jobs.pop(job.id, None)
        self.submit(list(entries), job.options)

    def _name(self, job: UiJob) -> None:
        """Give the job its video title when the page did not look the URL up first."""
        if job.title:
            return
        try:
            found = self.info(job.url, job.options.insecure)
        except AppError:
            return  # the download reports what is wrong with the URL
        with self._changed:
            self._describe(job, found)
            self._bump()

    @staticmethod
    def _describe(job: UiJob, found: VideoInfo | None) -> None:
        if found is not None:
            job.title = found.title
            job.video_id = found.id

    def _notify(self, job: UiJob, kind: str, details: dict) -> None:
        """Fold one structured download event into the job the page is watching."""
        with self._changed:
            if kind == "stage":
                job.stage, job.percent, job.processing = details["stage"], None, False
            elif kind == "progress":
                job.stage, job.percent, job.processing = details["stage"], details["percent"], False
            elif kind == "processing":
                job.percent, job.processing = None, True
            elif kind == "saved":
                job.files.append(Path(details["path"]))
            elif kind == "warning":
                job.warnings.append(details["message"])
            self._bump()

    def _log(self, job: UiJob, line: str) -> None:
        with self._changed:
            job.log.append(line.rstrip())
            job.log_count += 1
            self._bump()

    def _set(self, job: UiJob, **changes) -> None:
        with self._changed:
            for name, value in changes.items():
                setattr(job, name, value)
            if job.finished:
                job.processing = False
            self._bump()

    def _bump(self) -> None:
        """Callers hold the lock. Wakes everyone blocked in wait()."""
        self._revision += 1
        self._changed.notify_all()


def command_line(options: Options, url: str) -> str:
    """The `yt` command that does what this job does, to show under it in the page."""
    modes = options.modes
    if modes == ALL_MODES:
        words = ["all"]
    else:
        names = {
            "a": "mp3" if options.audio_format == "mp3" else "audio",
            "v": "mp4" if options.video_format == "mp4" else "video",
            "s": "sub",
        }
        words = [names[letter] for letter in modes]

    flags: list[str] = []

    def add(flag: str, key: str, value: str) -> None:
        if value != DEFAULTS[key]:
            flags.extend([flag, value])

    if "s" in modes:
        add("-l", "sub_langs", ",".join(options.sub_langs))
        add("-f", "sub_formats", ",".join(options.sub_formats))
        if not options.auto_subs:
            flags.append("--no-auto-subs")
    if "v" in modes:
        add("--vq", "video_quality", options.video_quality)
        add("--video-format", "video_format", options.video_format)
    if "a" in modes:
        add("--aq", "audio_quality", options.audio_quality)
        add("--audio-format", "audio_format", options.audio_format)

    argv = ["yt", *words, url, *flags, "-o", options.output]
    return subprocess.list2cmdline(argv) if sys.platform == "win32" else shlex.join(argv)


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0
