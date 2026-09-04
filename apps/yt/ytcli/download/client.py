from __future__ import annotations

import os
from collections.abc import Callable

from ..models import AppError, DownloadCancelled, SubtitleTracks

Logger = Callable[[str], None]
Cancelled = Callable[[], bool]

PROGRESS_STEP = 10.0


def ensure_ca_bundle() -> None:
    """Frozen builds have no system CA path, so point OpenSSL at certifi's bundle."""
    if os.environ.get("SSL_CERT_FILE"):
        return
    try:
        import certifi
    except ImportError:
        return
    bundle = certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", bundle)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", bundle)


def run_download(ydl_options: dict, url: str) -> None:
    """The single place yt-dlp actually downloads, which keeps it easy to fake in tests."""
    import yt_dlp

    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        ydl.download([url])


def list_subtitles(url: str, log: Logger | None = None, insecure: bool = False) -> SubtitleTracks:
    """Ask YouTube which subtitle languages a video offers, without downloading anything."""
    import yt_dlp

    ensure_ca_bundle()
    ydl_options = {
        "ignoreconfig": True,
        "quiet": True,
        "noprogress": True,
        "skip_download": True,
        "logger": YdlLogger(log or silent),
        "nocheckcertificate": insecure,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as error:  # yt-dlp raises many shapes of DownloadError
        raise AppError(f"Could not read video info: {error}") from error
    if not isinstance(info, dict):
        raise AppError("Could not read video info.")
    return SubtitleTracks(
        manual=tuple(sorted((info.get("subtitles") or {}).keys())),
        automatic=tuple(sorted((info.get("automatic_captions") or {}).keys())),
    )


def silent(_line: str) -> None:
    """Swallow yt-dlp chatter for calls that only need the return value."""


class YdlLogger:
    """Adapt yt-dlp's logger interface to our single log callback."""

    def __init__(self, log: Logger) -> None:
        self._log = log

    def debug(self, message: str) -> None:
        if not message.startswith("[debug] "):
            self._log(message)

    def info(self, message: str) -> None:
        self._log(message)

    def warning(self, message: str) -> None:
        self._log(f"warning: {message}")

    def error(self, message: str) -> None:
        self._log(f"error: {message}")


def progress_hook(log: Logger, cancelled: Cancelled | None) -> Callable[[dict], None]:
    """Report progress every 10% and abort the transfer when the user pressed Stop."""
    last = -PROGRESS_STEP

    def hook(event: dict) -> None:
        nonlocal last
        if cancelled is not None and cancelled():
            raise DownloadCancelled("stopped by the user")
        if event.get("status") == "finished":
            last = -PROGRESS_STEP
            log("  download finished, post-processing...")
            return
        if event.get("status") != "downloading":
            return
        total = event.get("total_bytes") or event.get("total_bytes_estimate")
        done = event.get("downloaded_bytes")
        if not total or not done:
            return
        percent = done * 100.0 / total
        if percent - last < PROGRESS_STEP:
            return
        last = percent
        log(f"  {percent:5.1f}%  of {total / 1_048_576:.1f} MiB")

    return hook
