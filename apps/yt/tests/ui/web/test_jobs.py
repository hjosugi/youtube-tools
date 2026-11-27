"""The download queue: what the page sees while jobs wait, run, finish and fail."""

from ytcli.settings import Options
from ytcli.ui.web import jobs as jobs_module
from ytcli.ui.web.jobs import command_line

from .conftest import PLAYLIST, wait_until


def options(tmp_path, **overrides) -> Options:
    return Options(output=str(tmp_path / "out"), modes="a", **overrides)


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
    assert manager.info(url).title == "Title of one"
    assert manager.info(url).title == "Title of one"
    (job,) = manager.submit([url], options(tmp_path))
    assert job.title == "Title of one"  # known before the worker even starts
    wait_until(lambda: only(manager)["status"] == "done")
    assert downloads.probed == [url]


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
    manager.submit([PLAYLIST], options(tmp_path))
    wait_until(lambda: len(downloads.calls) == 2 and not manager.active())
    _revision, listed = manager.snapshot()
    assert [job["url"] for job in listed] == ["https://y/watch?v=p1", "https://y/watch?v=p2"]
    assert all(job["status"] == "done" for job in listed)


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


def test_the_lookup_cache_stays_small(manager, monkeypatch):
    monkeypatch.setattr(jobs_module, "INFO_CACHE_SIZE", 3)
    for number in range(5):
        manager.info(f"https://y/watch?v={number}")
    assert len(manager._info) == 3


class TestCommandLine:
    """The line shown under a job: the same download as a command."""

    def test_words_for_the_usual_formats(self):
        assert command_line(Options(modes="a", output="/dl"), "URL") == "yt mp3 URL -o /dl"
        assert command_line(Options(modes="v", output="/dl"), "URL") == "yt mp4 URL -o /dl"
        assert command_line(Options(modes="s", output="/dl"), "URL") == "yt sub URL -o /dl"
        assert command_line(Options(modes="avs", output="/dl"), "URL") == "yt all URL -o /dl"
        assert command_line(Options(modes="as", output="/dl"), "URL") == "yt mp3 sub URL -o /dl"

    def test_other_formats_use_the_plain_words(self):
        line = command_line(Options(modes="av", output="/dl", audio_format="flac", video_format="mkv"), "URL")
        assert line == "yt audio video URL --video-format mkv --audio-format flac -o /dl"

    def test_only_settings_that_differ_from_the_defaults_are_spelled_out(self):
        chosen = Options(
            modes="avs",
            output="/dl",
            sub_langs=("ja", "en"),
            sub_formats=("srt",),
            auto_subs=False,
            video_quality="1080",
            audio_quality="192",
        )
        assert command_line(chosen, "URL") == (
            "yt all URL -l ja,en -f srt --no-auto-subs --vq 1080 --aq 192 -o /dl"
        )

    def test_flags_of_modes_not_asked_for_are_left_out(self):
        chosen = Options(modes="s", output="/dl", video_quality="720", audio_quality="64")
        assert command_line(chosen, "URL") == "yt sub URL -o /dl"

    def test_the_url_is_quoted_for_the_shell(self, monkeypatch):
        monkeypatch.setattr(jobs_module.sys, "platform", "linux")
        assert "'https://y/watch?v=a&t=1'" in command_line(Options(modes="a"), "https://y/watch?v=a&t=1")
        monkeypatch.setattr(jobs_module.sys, "platform", "win32")
        assert command_line(Options(modes="a", output="C:\\My Files"), "URL").endswith('-o "C:\\My Files"')
