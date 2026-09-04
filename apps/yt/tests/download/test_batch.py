"""The URL loop both the CLI and the GUI run on."""

import pytest

from ytcli.download import batch
from ytcli.models import AppError, DownloadCancelled, DownloadResult
from ytcli.settings import Options


@pytest.fixture
def log():
    """Collect the log lines a run produced."""
    return []


@pytest.fixture
def errors():
    """Collect the lines a run sent to the error channel."""
    return []


def options(*urls: str) -> Options:
    return Options(urls=list(urls))


def stub(monkeypatch, handler):
    """Replace the per-URL download with a callable taking the URL."""
    monkeypatch.setattr(batch, "download", lambda opts, url, *args, **kwargs: handler(url))


def test_every_url_is_downloaded(monkeypatch, log):
    seen: list[str] = []

    def handler(url):
        seen.append(url)
        return DownloadResult(url=url, files=["a.srt", "a.tsv"])

    stub(monkeypatch, handler)
    report = batch.download_all(options("one", "two"), log.append)

    assert seen == ["one", "two"]
    assert report.saved == 4
    assert report.failed == 0
    assert report.exit_code == 0


def test_warnings_are_logged(monkeypatch, log):
    stub(monkeypatch, lambda url: DownloadResult(url=url, files=["a.srt"], warnings=["heads up"]))
    batch.download_all(options("one"), log.append)

    assert "note: heads up" in log


def test_a_failing_url_does_not_stop_the_rest(monkeypatch, log, errors):
    def handler(url):
        if url == "one":
            raise AppError("nope")
        return DownloadResult(url=url, files=["a.srt"])

    stub(monkeypatch, handler)
    report = batch.download_all(options("one", "two"), log.append, errors.append)

    assert report.saved == 1
    assert report.failed == 1
    assert report.exit_code == 1
    assert errors == ["error (one): nope"]


def test_an_unexpected_error_is_reported_like_any_other(monkeypatch, log, errors):
    stub(monkeypatch, lambda url: (_ for _ in ()).throw(ValueError("weird")))
    report = batch.download_all(options("one"), log.append, errors.append)

    assert report.failed == 1
    assert "unexpected error (one): weird" in errors


def test_failures_reach_the_log_when_there_is_no_error_channel(monkeypatch, log):
    stub(monkeypatch, lambda url: (_ for _ in ()).throw(AppError("nope")))
    batch.download_all(options("one"), log.append)

    assert "error (one): nope" in log


def test_a_cancelled_download_stops_the_loop(monkeypatch, log):
    seen: list[str] = []

    def handler(url):
        seen.append(url)
        raise DownloadCancelled("stopped by the user")

    stub(monkeypatch, handler)
    report = batch.download_all(options("one", "two"), log.append)

    assert seen == ["one"]
    assert report.cancelled is True
    assert report.exit_code == 0


def test_a_cancelled_run_never_starts(monkeypatch, log):
    stub(monkeypatch, lambda url: pytest.fail("should not download"))
    report = batch.download_all(options("one"), log.append, cancelled=lambda: True)

    assert report.cancelled is True
    assert log == []
