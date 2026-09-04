from __future__ import annotations

from dataclasses import dataclass

from ..models import AppError, DownloadCancelled
from ..settings import Options
from .client import Cancelled, Logger
from .runner import download


@dataclass
class BatchReport:
    """What a run over several URLs produced."""

    saved: int = 0
    failed: int = 0
    cancelled: bool = False

    @property
    def exit_code(self) -> int:
        return 1 if self.failed else 0


def download_all(
    options: Options,
    log: Logger = print,
    report_error: Logger | None = None,
    cancelled: Cancelled | None = None,
) -> BatchReport:
    """Download every URL in turn, so one failure never stops the rest of the list."""
    # The CLI sends failures to stderr; the GUI has only the one log pane.
    report_error = report_error or log
    report = BatchReport()

    for url in options.urls:
        if cancelled is not None and cancelled():
            report.cancelled = True
            break
        log(f"\n=== {url}")
        try:
            result = download(options, url, log, cancelled)
        except DownloadCancelled:
            report.cancelled = True
            break
        except AppError as error:
            report_error(f"error ({url}): {error}")
            report.failed += 1
            continue
        except Exception as error:  # yt-dlp and ffmpeg raise a wide range of errors
            report_error(f"unexpected error ({url}): {error}")
            report.failed += 1
            continue
        report.saved += len(result.files)
        for warning in result.warnings:
            log(f"note: {warning}")

    return report
