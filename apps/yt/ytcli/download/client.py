from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from urllib.parse import parse_qs, urlparse

from ..models import AppError, DownloadCancelled, Notify, SubtitleTracks, VideoInfo

Logger = Callable[[str], None]
Cancelled = Callable[[], bool]

PROGRESS_STEP = 10.0

# yt-dlp solves YouTube's JavaScript challenges with an external runtime but enables only
# deno by default. Enabling whichever of these is installed avoids "formats may be missing".
JS_RUNTIMES = {"deno": "deno", "node": "node", "bun": "bun", "quickjs": "qjs"}


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


def js_runtimes() -> dict[str, dict]:
    """The JavaScript runtimes found on PATH, in the shape yt-dlp expects."""
    found = {name: {} for name, executable in JS_RUNTIMES.items() if shutil.which(executable)}
    return found or {"deno": {}}


def base_options(log: Logger, insecure: bool = False) -> dict:
    """The yt-dlp options every call shares, whether it downloads or only looks."""
    return {
        "ignoreconfig": True,
        "quiet": True,
        "noprogress": True,
        "consoletitle": False,
        "logger": YdlLogger(log),
        "nocheckcertificate": insecure,
        # A watch URL that carries &list=... means that one video, not the whole playlist.
        "noplaylist": True,
        "js_runtimes": js_runtimes(),
    }


def run_download(ydl_options: dict, url: str) -> None:
    """The single place yt-dlp actually downloads, which keeps it easy to fake in tests."""
    import yt_dlp

    with yt_dlp.YoutubeDL(ydl_options) as ydl:
        ydl.download([url])


def extract_info(url: str, log: Logger | None = None, insecure: bool = False) -> dict:
    """The single place yt-dlp looks a URL up without downloading it."""
    import yt_dlp

    ensure_ca_bundle()
    ydl_options = base_options(log or silent, insecure)
    # Playlists come back as a list of entries instead of one full extraction per video.
    ydl_options.update({"skip_download": True, "extract_flat": "in_playlist"})
    try:
        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as error:  # yt-dlp raises many shapes of DownloadError
        raise AppError(f"Could not read video info: {error}") from error
    if not isinstance(info, dict):
        raise AppError("Could not read video info.")
    return info


def probe(url: str, log: Logger | None = None, insecure: bool = False) -> VideoInfo:
    """Title, thumbnail and subtitle languages of a URL, or the videos of a playlist."""
    info = extract_info(url, log, insecure)
    entries = tuple(
        target
        for entry in (info.get("entries") or ())
        if isinstance(entry, dict) and (target := entry.get("url") or entry.get("webpage_url"))
    )
    return VideoInfo(
        url=url,
        id=str(info.get("id") or ""),
        title=str(info.get("title") or ""),
        uploader=str(info.get("uploader") or info.get("channel") or ""),
        duration=int(info.get("duration") or 0),
        thumbnail=str(info.get("thumbnail") or ""),
        tracks=SubtitleTracks(
            manual=tuple(sorted((info.get("subtitles") or {}).keys())),
            automatic=tuple(sorted((info.get("automatic_captions") or {}).keys())),
        ),
        entries=entries,
    )


def list_subtitles(url: str, log: Logger | None = None, insecure: bool = False) -> SubtitleTracks:
    """Ask YouTube which subtitle languages a video offers, without downloading anything."""
    return probe(url, log, insecure).tracks


def is_playlist_url(url: str) -> bool:
    """True for a link to a playlist itself, false for a video that merely sits in one."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return "list" in query and "v" not in query and parsed.path.rstrip("/").endswith("/playlist")


def expand_playlist(url: str, log: Logger | None = None, insecure: bool = False) -> list[str]:
    """Turn a playlist URL into its video URLs; any other URL comes back unchanged."""
    if not is_playlist_url(url):
        return [url]
    return list(probe(url, log, insecure).entries) or [url]


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
        # yt-dlp says this on every call; we fetch ffmpeg ourselves when a stage needs it.
        if message.startswith("ffmpeg not found"):
            return
        self._log(f"warning: {message}")

    def error(self, message: str) -> None:
        self._log(f"error: {message}")


def progress_hook(
    log: Logger,
    cancelled: Cancelled | None,
    notify: Notify | None = None,
    stage: str = "",
) -> Callable[[dict], None]:
    """Report progress every 10% and abort the transfer when the user pressed Stop."""
    last = -PROGRESS_STEP

    def hook(event: dict) -> None:
        nonlocal last
        if cancelled is not None and cancelled():
            raise DownloadCancelled("stopped by the user")
        if event.get("status") == "finished":
            last = -PROGRESS_STEP
            log("  download finished, post-processing...")
            if notify is not None:
                notify("processing", {"stage": stage})
            return
        if event.get("status") != "downloading":
            return
        total = event.get("total_bytes") or event.get("total_bytes_estimate")
        done = event.get("downloaded_bytes")
        if not total or not done:
            return
        percent = done * 100.0 / total
        if notify is not None:
            notify(
                "progress",
                {
                    "stage": stage,
                    "percent": round(min(percent, 100.0), 1),
                    "total": int(total),
                    "speed": event.get("speed") or 0,
                    "eta": event.get("eta") or 0,
                },
            )
        if percent - last < PROGRESS_STEP:
            return
        last = percent
        log(f"  {percent:5.1f}%  of {total / 1_048_576:.1f} MiB")

    return hook
