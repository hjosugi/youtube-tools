"""The download queue: what the page sees while jobs wait, run, finish and fail."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from ytcli.models import AppError
from ytcli.settings import Options
from ytcli.ui.web import jobs as jobs_module

from .conftest import PLAYLIST, wait_until


def options(tmp_path, modes="a", **overrides) -> Options:
    return Options(output=str(tmp_path / "out"), modes=modes, **overrides)


def only(manager) -> dict:
    _revision, listed = manager.snapshot()
    assert len(listed) == 1
    return listed[0]


def test_a_job_runs_and_reports_its_file(tmp_path, manager, downloads):
    (job,) = manager.submit(["https://y/watch?v=one"], options(tmp_path))
    wait_until(lambda: only(manager)["status"] == "done")

    seen = only(manager)
    assert seen["id"] == job.id
    assert seen["files"] == [{"name": "one.mp3", "size": 2048}]
    assert seen["folder"] == str(tmp_path / "out")
    assert (seen["percent"], seen["processing"]) == (100.0, False)
    assert seen["title"] == "Title of one"  # looked up because the page had not asked first
    assert seen["video_id"] == "abcdefghijk"
    assert manager.log_lines(job.id) == ["starting https://y/watch?v=one"]
    assert seen["log_count"] == 1
    assert not manager.active()


def test_each_job_keeps_the_options_it_was_started_with(tmp_path, manager, downloads):
    chosen = options(tmp_path)
    manager.submit(["https://y/watch?v=one"], chosen)
    chosen.modes = "v"
    wait_until(lambda: only(manager)["status"] == "done")
    sent, url = downloads.calls[0]
    assert (sent.modes, sent.urls, url) == ("a", ["https://y/watch?v=one"], "https://y/watch?v=one")


def test_a_lookup_from_the_page_is_reused(tmp_path, manager, downloads):
    url = "https://y/watch?v=one"
    info = manager.info(url)
    assert info.title == "Title of one"
    assert manager.info(url).title == "Title of one"
    (job,) = manager.submit([url], options(tmp_path, modes="as"))
    assert job.title == "Title of one"  # known before the worker even starts
    wait_until(lambda: only(manager)["status"] == "done")
    assert downloads.probed == [url]
    assert downloads.tracks == [info.tracks]


def test_a_download_joins_an_unfinished_preview(tmp_path, manager, downloads, monkeypatch):
    started, release = threading.Event(), threading.Event()
    url = "https://y/watch?v=one"

    def probe(url, insecure):
        started.set()
        assert release.wait(5)
        return downloads.probe(url, insecure=insecure)

    monkeypatch.setattr(manager, "_probe", probe)
    with ThreadPoolExecutor() as pool:
        preview = pool.submit(manager.info, url)
        try:
            assert started.wait(5)
            manager.submit([url], options(tmp_path, modes="s"))
            wait_until(lambda: only(manager)["status"] == "running")
        finally:
            release.set()
        tracks = preview.result().tracks
    wait_until(lambda: not manager.active())
    assert downloads.probed == [url]
    assert downloads.tracks == [tracks]


def test_a_failed_lookup_can_be_retried(manager, downloads, monkeypatch):
    url = "https://y/watch?v=one"

    def unavailable(url, insecure):
        raise AppError("unavailable")

    monkeypatch.setattr(manager, "_probe", unavailable)
    with pytest.raises(AppError, match="unavailable"):
        manager.info(url)
    monkeypatch.setattr(manager, "_probe", downloads.probe)
    assert manager.info(url).title == "Title of one"


def test_a_verified_lookup_does_not_reuse_an_insecure_result(manager, downloads):
    url = "https://y/watch?v=one"
    manager.info(url, insecure=True)
    manager.info(url)
    assert downloads.probed == [url, url]


def test_progress_is_visible_while_a_job_runs(tmp_path, manager, downloads):
    downloads.hold.clear()
    manager.submit(["https://y/watch?v=one"], options(tmp_path))
    wait_until(lambda: only(manager)["percent"] == 40.0)
    running = only(manager)
    assert (running["status"], running["stage"]) == ("running", "audio")
    assert manager.active()
    downloads.hold.set()
    wait_until(lambda: only(manager)["status"] == "done")


def test_a_failure_is_shown_and_the_queue_moves_on(tmp_path, manager):
    manager.submit(
        ["https://y/watch?v=fail", "https://y/watch?v=crash", "https://y/watch?v=ok"], options(tmp_path)
    )
    wait_until(lambda: not manager.active())
    _revision, listed = manager.snapshot()
    assert [job["status"] for job in listed] == ["failed", "failed", "done"]
    assert listed[0]["error"] == "Nothing was downloaded."
    assert listed[1]["error"] == "unexpected error: weird"


def test_warnings_reach_the_page(tmp_path, manager):
    manager.submit(["https://y/watch?v=warn"], options(tmp_path))
    wait_until(lambda: only(manager)["status"] == "done")
    assert only(manager)["warnings"] == ["no ja subtitles"]


def test_a_url_that_cannot_be_looked_up_still_gets_its_download_error(tmp_path, manager):
    manager.submit(["https://y/watch?v=unknown-fail"], options(tmp_path))
    wait_until(lambda: not manager.active())
    seen = only(manager)
    assert (seen["status"], seen["title"]) == ("failed", "")


def test_stopping_a_running_job(tmp_path, manager, downloads):
    downloads.hold.clear()
    (job,) = manager.submit(["https://y/watch?v=one"], options(tmp_path))
    assert downloads.started.wait(5)
    assert manager.cancel(job.id) is True
    wait_until(lambda: only(manager)["status"] == "cancelled")
    assert manager.cancel(job.id) is False  # nothing left to stop


def test_stopping_a_waiting_job_never_starts_it(tmp_path, manager, downloads):
    downloads.hold.clear()
    first, second = manager.submit(["https://y/watch?v=one", "https://y/watch?v=two"], options(tmp_path))
    assert downloads.started.wait(5)
    assert manager.cancel(second.id) is True
    assert manager.get(second.id).status == "cancelled"
    downloads.hold.set()
    wait_until(lambda: not manager.active())
    assert [url for _options, url in downloads.calls] == ["https://y/watch?v=one"]
    assert manager.cancel("999") is False


def test_a_playlist_becomes_one_job_per_video(tmp_path, manager, downloads):
    manager.info(PLAYLIST)  # the preview has already read the playlist once
    manager.submit([PLAYLIST], options(tmp_path))
    wait_until(lambda: len(downloads.calls) == 2 and not manager.active())
    _revision, listed = manager.snapshot()
    assert [job["url"] for job in listed] == ["https://y/watch?v=p1", "https://y/watch?v=p2"]
    assert all(job["status"] == "done" for job in listed)
    assert [job["title"] for job in listed] == ["p1", "p2"]
    assert downloads.probed == [PLAYLIST]


def test_playlist_subtitles_use_each_videos_own_tracks(tmp_path, manager, downloads):
    manager.submit([PLAYLIST], options(tmp_path, modes="s"))
    wait_until(lambda: not manager.active())
    assert downloads.probed == [PLAYLIST, "https://y/watch?v=p1", "https://y/watch?v=p2"]
    assert len(downloads.tracks) == 2
    assert all(tracks and tracks.manual == ("en",) for tracks in downloads.tracks)


def test_cancelling_during_playlist_lookup_never_queues_its_children(
    tmp_path, manager, downloads, monkeypatch
):
    started, release = threading.Event(), threading.Event()

    def probe(url, insecure):
        started.set()
        assert release.wait(5)
        return downloads.probe(url, insecure=insecure)

    monkeypatch.setattr(manager, "_probe", probe)
    (job,) = manager.submit([PLAYLIST], options(tmp_path))
    try:
        assert started.wait(5)
        assert manager.cancel(job.id)
    finally:
        release.set()
    wait_until(lambda: not manager.active())
    assert only(manager)["status"] == "cancelled"
    assert downloads.calls == []


def test_clearing_keeps_what_is_still_running(tmp_path, manager, downloads):
    manager.submit(["https://y/watch?v=done"], options(tmp_path))
    wait_until(lambda: not manager.active())
    downloads.hold.clear()
    manager.submit(["https://y/watch?v=busy"], options(tmp_path))
    manager.clear()
    assert only(manager)["url"] == "https://y/watch?v=busy"
    assert manager.log_lines("1") is None


def test_wait_returns_when_something_changes_or_time_is_up(tmp_path, manager):
    revision, _jobs = manager.snapshot()
    assert manager.wait(revision, 0.05) == revision
    manager.submit(["https://y/watch?v=one"], options(tmp_path))
    assert manager.wait(revision, 5) != revision


def test_a_closed_queue_never_accepts_a_job(tmp_path, manager):
    manager.shutdown()
    with pytest.raises(AppError, match="shutting down"):
        manager.submit(["https://y/watch?v=one"], options(tmp_path))
    assert not manager.active()


def test_the_lookup_cache_stays_small(manager, monkeypatch):
    monkeypatch.setattr(jobs_module, "INFO_CACHE_SIZE", 3)
    for number in range(5):
        manager.info(f"https://y/watch?v={number}")
    assert len(manager._info) == 3
