import pytest

from ytcli.download import client
from ytcli.models import DownloadCancelled


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
