import pytest

from ytcli.download import client
from ytcli.models import DownloadCancelled, SubtitleTracks, VideoInfo


def test_ensure_ca_bundle_sets_the_variables_once(monkeypatch):
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    client.ensure_ca_bundle()
    first = client.os.environ["SSL_CERT_FILE"]
    client.ensure_ca_bundle()
    assert client.os.environ["SSL_CERT_FILE"] == first


def test_ensure_ca_bundle_respects_an_existing_setting(monkeypatch):
    monkeypatch.setenv("SSL_CERT_FILE", "/my/bundle.pem")
    client.ensure_ca_bundle()
    assert client.os.environ["SSL_CERT_FILE"] == "/my/bundle.pem"


class TestYdlLogger:
    def test_forwards_messages_and_labels_problems(self):
        lines: list[str] = []
        logger = client.YdlLogger(lines.append)
        logger.info("downloading")
        logger.warning("slow")
        logger.error("gone")
        assert lines == ["downloading", "warning: slow", "error: gone"]

    def test_swallows_yt_dlp_debug_noise(self):
        lines: list[str] = []
        logger = client.YdlLogger(lines.append)
        logger.debug("[debug] internal")
        logger.debug("real message")
        assert lines == ["real message"]


class TestProgressHook:
    def test_reports_in_ten_percent_steps(self):
        lines: list[str] = []
        hook = client.progress_hook(lines.append, None)
        for done in range(0, 1001, 10):
            hook({"status": "downloading", "downloaded_bytes": done, "total_bytes": 1000})
        assert 8 <= len(lines) <= 11

    def test_ignores_events_without_a_size(self):
        lines: list[str] = []
        hook = client.progress_hook(lines.append, None)
        hook({"status": "downloading"})
        hook({"status": "downloading", "downloaded_bytes": 5})
        assert lines == []

    def test_announces_post_processing_and_resets(self):
        lines: list[str] = []
        hook = client.progress_hook(lines.append, None)
        hook({"status": "downloading", "downloaded_bytes": 900, "total_bytes": 1000})
        hook({"status": "finished"})
        hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 1000})
        assert "post-processing" in lines[1]
        assert len(lines) == 3

    def test_raises_when_the_user_asked_to_stop(self):
        hook = client.progress_hook(lambda _line: None, lambda: True)
        with pytest.raises(DownloadCancelled):
            hook({"status": "downloading", "downloaded_bytes": 1, "total_bytes": 10})


def test_silent_swallows_everything():
    assert client.silent("anything") is None


class TestNotify:
    def collect(self):
        events: list[tuple[str, dict]] = []
        hook = client.progress_hook(
            lambda _line: None, None, lambda kind, details: events.append((kind, details)), "audio"
        )
        return events, hook

    def test_every_progress_event_is_forwarded_with_its_stage(self):
        events, hook = self.collect()
        hook({"status": "downloading", "total_bytes": 200, "downloaded_bytes": 50, "speed": 10, "eta": 15})
        hook({"status": "downloading", "total_bytes": 200, "downloaded_bytes": 52})
        assert [kind for kind, _details in events] == ["progress", "progress"]
        assert events[0][1] == {"stage": "audio", "percent": 25.0, "total": 200, "speed": 10, "eta": 15}

    def test_the_end_of_a_transfer_means_converting(self):
        events, hook = self.collect()
        hook({"status": "finished"})
        assert events == [("processing", {"stage": "audio"})]

    def test_an_estimate_never_passes_one_hundred_percent(self):
        events, hook = self.collect()
        hook({"status": "downloading", "total_bytes_estimate": 100, "downloaded_bytes": 130})
        assert events[0][1]["percent"] == 100.0


def test_the_ffmpeg_reminder_is_dropped_but_other_warnings_stay():
    lines: list[str] = []
    logger = client.YdlLogger(lines.append)
    logger.warning("ffmpeg not found. The downloaded format may not be the best available.")
    logger.warning("something else")
    assert lines == ["warning: something else"]


def test_installed_javascript_runtimes_are_enabled(monkeypatch):
    monkeypatch.setattr(client.shutil, "which", lambda name: "/bin/x" if name in ("node", "qjs") else None)
    assert client.js_runtimes() == {"node": {}, "quickjs": {}}


def test_without_any_runtime_yt_dlp_keeps_its_default(monkeypatch):
    monkeypatch.setattr(client.shutil, "which", lambda _name: None)
    assert client.js_runtimes() == {"deno": {}}


def test_a_watch_url_inside_a_playlist_means_that_one_video():
    options = client.base_options(lambda _line: None)
    assert options["noplaylist"] is True
    assert options["ignoreconfig"] is True


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/playlist?list=PL123", True),
        ("https://youtube.com/playlist/?list=PL123", True),
        ("https://www.youtube.com/watch?v=abc&list=PL123", False),
        ("https://www.youtube.com/watch?v=abc", False),
        ("https://youtu.be/abc", False),
        ("https://www.youtube.com/playlist", False),
    ],
)
def test_only_a_link_to_the_playlist_itself_is_a_playlist(url, expected):
    assert client.is_playlist_url(url) is expected


def test_probe_reads_what_the_ui_shows(monkeypatch):
    monkeypatch.setattr(
        client,
        "extract_info",
        lambda url, log=None, insecure=False: {
            "id": "abc",
            "title": "A talk",
            "channel": "Someone",
            "duration": 61.4,
            "thumbnail": "https://i.ytimg.com/vi/abc/hq.jpg",
            "subtitles": {"ja": [], "en": []},
            "automatic_captions": {"en": []},
        },
    )
    assert client.probe("URL") == VideoInfo(
        url="URL",
        id="abc",
        title="A talk",
        uploader="Someone",
        duration=61,
        thumbnail="https://i.ytimg.com/vi/abc/hq.jpg",
        tracks=SubtitleTracks(manual=("en", "ja"), automatic=("en",)),
    )


def test_probe_lists_the_videos_of_a_playlist(monkeypatch):
    info = {"title": "Mix", "entries": [{"url": "u1"}, {"webpage_url": "u2"}, {"id": "no-url"}, None]}
    monkeypatch.setattr(client, "extract_info", lambda *args, **kwargs: info)
    assert client.probe("LIST").entries == ("u1", "u2")
    assert client.list_subtitles("LIST") == SubtitleTracks()


def test_a_playlist_expands_and_anything_else_is_left_alone(monkeypatch):
    asked: list[str] = []

    def probe(url, log=None, insecure=False):
        asked.append(url)
        return VideoInfo(url=url, entries=("u1", "u2"))

    monkeypatch.setattr(client, "probe", probe)
    assert client.expand_playlist("https://www.youtube.com/watch?v=abc") == [
        "https://www.youtube.com/watch?v=abc"
    ]
    assert asked == []
    assert client.expand_playlist("https://www.youtube.com/playlist?list=PL1") == ["u1", "u2"]


def test_an_empty_playlist_is_left_for_the_download_to_report(monkeypatch):
    monkeypatch.setattr(client, "probe", lambda url, log=None, insecure=False: VideoInfo(url=url))
    url = "https://www.youtube.com/playlist?list=PL1"
    assert client.expand_playlist(url) == [url]
