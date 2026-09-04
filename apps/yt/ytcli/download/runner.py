from __future__ import annotations

import tempfile
from pathlib import Path

from ..models import AppError, DownloadResult
from ..settings import Options
from .client import Cancelled, Logger, ensure_ca_bundle
from .job import Job
from .stages import fetch_media, fetch_subtitles

# Subtitles first: they are cheap, so a later media failure still leaves something useful.
STAGE_ORDER = (("s", "subtitle"), ("a", "audio"), ("v", "video"))


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
        for letter, kind in STAGE_ORDER:
            if letter not in options.modes:
                continue
            job.check_cancelled()
            if kind == "subtitle":
                fetch_subtitles(job)
            else:
                fetch_media(job, kind)

    if not result.files:
        raise AppError(
            "Nothing was downloaded. " + (" ".join(result.warnings) or "yt-dlp produced no files.")
        )
    return result
