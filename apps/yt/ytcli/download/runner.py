from __future__ import annotations

import tempfile
from collections.abc import Callable
from functools import partial
from pathlib import Path

from ..models import AppError, DownloadResult
from ..settings import Options
from .client import Cancelled, Logger, ensure_ca_bundle
from .job import Job
from .stages import fetch_media, fetch_subtitles

# Subtitles first: they are cheap, so a later media failure still leaves something useful.
STAGES: tuple[tuple[str, Callable[[Job], None]], ...] = (
    ("s", fetch_subtitles),
    ("a", partial(fetch_media, kind="audio")),
    ("v", partial(fetch_media, kind="video")),
)


def download(
    options: Options,
    url: str,
    log: Logger = print,
    cancelled: Cancelled | None = None,
) -> DownloadResult:
    """Download every requested mode for one URL into options.out_dir."""
    if not options.modes:
        raise AppError("Nothing to do: no mode selected.")

    ensure_ca_bundle()
    result = DownloadResult(url=url)
    options.out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="yt-") as staging:
        job = Job(options, url, Path(staging), result, log, cancelled)
        for letter, fetch in STAGES:
            if letter not in options.modes:
                continue
            job.check_cancelled()
            fetch(job)

    if not result.files:
        raise AppError(
            "Nothing was downloaded. " + (" ".join(result.warnings) or "yt-dlp produced no files.")
        )
    return result
