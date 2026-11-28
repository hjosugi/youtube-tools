"""The download queue behind the web UI: one worker thread and jobs the page can watch."""

from __future__ import annotations

import itertools
import queue
import threading
from collections import deque
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import dataclass, field, replace
from functools import cached_property
from pathlib import Path

from ...download import download, is_playlist_url, probe
from ...models import AppError, DownloadCancelled, VideoInfo
from ...settings import Options
from ..args import command_line

LOG_LINES = 400
INFO_CACHE_SIZE = 64
FINISHED = ("done", "failed", "cancelled")


@dataclass(frozen=True)
class SavedFile:
    """A finished file and its size, measured once when it was saved."""

    path: Path
    size: int


@dataclass
class UiJob:
    """One URL being downloaded, in the shape the page draws it."""

    id: str
    url: str
    options: Options
    command: str  # the same download as a `yt` command, shown under the job
    title: str = ""
    video_id: str = ""
    status: str = "queued"  # queued, running, done, failed or cancelled
    stage: str = ""  # subtitle, audio, video, ffmpeg or playlist
    percent: float | None = None
    processing: bool = False
    files: list[SavedFile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str = ""
    log: deque[str] = field(default_factory=lambda: deque(maxlen=LOG_LINES))
    log_count: int = 0
    stop: threading.Event = field(default_factory=threading.Event)

    @property
    def finished(self) -> bool:
        return self.status in FINISHED

    @cached_property
    def folder(self) -> Path:
        return self.options.out_dir

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
            "files": [{"name": saved.path.name, "size": saved.size} for saved in self.files],
            "folder": str(self.folder),
            "warnings": list(self.warnings),
            "error": self.error,
            "command": self.command,
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
        self._info: dict[tuple[str, bool], VideoInfo] = {}
        self._looking: dict[tuple[str, bool], Future[VideoInfo]] = {}
        self._closed = False
        self._worker = threading.Thread(target=self._work, daemon=True, name="yt-downloads")
        self._worker.start()

    # ---- what the HTTP handlers call -------------------------------------------------

    def info(self, url: str, insecure: bool = False) -> VideoInfo:
        """Look a URL up once and remember the answer for the job that follows.

        A second caller for the same URL waits for the first instead of asking YouTube
        again, which is what happens when a button is pressed before the preview arrived.
        """
        key = (url, insecure)
        with self._changed:
            cached = self._info.get(key)
            if cached is not None:
                return cached
            pending = self._looking.get(key)
            if pending is None:
                lookup = self._looking[key] = Future()
        if pending is not None:
            return pending.result()

        try:
            found = self._probe(url, insecure=insecure)
            with self._changed:
                self._info[key] = found
                if len(self._info) > INFO_CACHE_SIZE:
                    self._info.pop(next(iter(self._info)))
            lookup.set_result(found)
            return found
        except BaseException as error:
            lookup.set_exception(error)  # release every waiter, also when the lookup fails
            raise
        finally:
            with self._changed:
                del self._looking[key]

    def submit(self, urls: list[str], options: Options) -> list[UiJob]:
        """Queue one job per URL, each with its own copy of the options."""
        with self._changed:
            if self._closed:
                raise AppError("The download queue is shutting down.")
            jobs = [self._enqueue(url, options) for url in urls]
            self._bump()
        return jobs

    def _enqueue(self, url: str, options: Options, entry: VideoInfo | None = None) -> UiJob:
        """Add one job while holding the queue lock. Prefer full metadata to a playlist entry."""
        frozen = replace(options, urls=[url])
        job = UiJob(str(next(self._ids)), url, frozen, command_line(frozen, url))
        self._describe(job, self._info.get((url, options.insecure)) or entry)
        self._jobs[job.id] = job
        self._pending.put(job)
        return job

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
            if not self._closed:
                self._closed = True
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
            with self._changed:
                if job.stop.is_set():
                    self._set(job, status="cancelled")
                    continue
                self._set(job, status="running")
            self._run(job)

    def _run(self, job: UiJob) -> None:
        try:
            if is_playlist_url(job.url):
                self._expand(job)
                return
            found = self._look_up(job)
            if job.stop.is_set():
                raise DownloadCancelled("stopped by the user")
            self._download(
                job.options,
                job.url,
                lambda line: self._log(job, line),
                job.stop.is_set,
                lambda kind, details: self._notify(job, kind, details),
                found.tracks if found else None,
            )
        except DownloadCancelled:
            self._set(job, status="cancelled")
        except AppError as error:
            self._set(job, status="failed", error=str(error))
        except Exception as error:  # yt-dlp and ffmpeg raise a wide range of errors
            self._set(job, status="failed", error=f"unexpected error: {error}")
        else:
            # The files and warnings arrived as events while the download ran.
            self._set(job, status="done", percent=100.0)

    def _expand(self, job: UiJob) -> None:
        """Replace a playlist job with one job per video."""
        self._set(job, stage="playlist")
        entries = self.info(job.url, job.options.insecure).entries
        with self._changed:
            if job.stop.is_set():
                raise DownloadCancelled("stopped by the user")
            if not entries:
                raise AppError("This playlist has no videos.")
            self._jobs.pop(job.id, None)
            for entry in entries:
                self._enqueue(entry.url, job.options, entry)
            self._bump()

    def _look_up(self, job: UiJob) -> VideoInfo | None:
        """The video's details, when the job still needs something from them.

        That is its title, unless the page or the playlist already supplied one, and the
        subtitle languages, which the download would otherwise ask YouTube for again.
        """
        if job.title and "s" not in job.options.modes:
            return None
        try:
            found = self.info(job.url, job.options.insecure)
        except AppError:
            return None  # the download reports what is wrong with the URL
        with self._changed:
            if not job.title:
                self._describe(job, found)
                self._bump()
        return found

    @staticmethod
    def _describe(job: UiJob, found: VideoInfo | None) -> None:
        if found is not None:
            job.title = found.title
            job.video_id = found.id

    def _notify(self, job: UiJob, kind: str, details: dict) -> None:
        """Fold one structured download event into the job the page is watching."""
        saved = None
        if kind == "saved":
            path = Path(details["path"])
            saved = SavedFile(path, _size(path))  # stat before taking the lock
        with self._changed:
            before = (job.stage, job.percent, job.processing, len(job.files), len(job.warnings))
            if kind == "stage":
                job.stage, job.percent, job.processing = details["stage"], None, False
            elif kind == "progress":
                job.stage, job.percent, job.processing = details["stage"], details["percent"], False
            elif kind == "processing":
                job.percent, job.processing = None, True
            elif saved is not None:
                job.files.append(saved)
            elif kind == "warning":
                job.warnings.append(details["message"])
            # yt-dlp reports far more often than the rounded percentage moves.
            if before != (job.stage, job.percent, job.processing, len(job.files), len(job.warnings)):
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


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0
