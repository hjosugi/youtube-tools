"""A fake download and a running UI server, shared by the web UI tests."""

import http.client
import json
import threading
import time
from pathlib import Path

import pytest

from ytcli.models import AppError, DownloadCancelled, DownloadResult, SubtitleTracks, VideoInfo
from ytcli.settings import Options
from ytcli.ui.web.jobs import JobManager
from ytcli.ui.web.server import App, UiServer

PLAYLIST = "https://www.youtube.com/playlist?list=PL1"


def wait_until(predicate, timeout: float = 5.0) -> None:
    """Poll until the worker thread has caught up, failing loudly when it never does."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("timed out waiting for the UI to catch up")


class FakeDownloads:
    """Stands in for yt-dlp: writes one file per job, or fails, or waits to be released."""

    def __init__(self) -> None:
        self.calls: list[tuple[Options, str]] = []
        self.probed: list[str] = []
        self.hold = threading.Event()
        self.hold.set()  # clear it to keep a job "running" until the test lets go
        self.started = threading.Event()

    def download(self, options, url, log, cancelled, notify):
        self.calls.append((options, url))
        self.started.set()
        log(f"starting {url}")
        notify("stage", {"stage": "audio"})
        notify("progress", {"stage": "audio", "percent": 40.0})
        while not self.hold.wait(0.01):
            if cancelled():
                raise DownloadCancelled("stopped by the user")
        if "fail" in url:
            raise AppError("Nothing was downloaded.")
        if "crash" in url:
            raise ValueError("weird")
        options.out_dir.mkdir(parents=True, exist_ok=True)
        target = options.out_dir / f"{url.rsplit('=', 1)[-1]}.mp3"
        target.write_bytes(b"x" * 2048)
        notify("processing", {"stage": "audio"})
        notify("saved", {"path": str(target)})
        return DownloadResult(url=url, files=[target], warnings=["no ja subtitles"] if "warn" in url else [])

    def probe(self, url, log=None, insecure=False):
        self.probed.append(url)
        if "unknown" in url:
            raise AppError("Could not read video info: gone")
        if url == PLAYLIST:
            return VideoInfo(url=url, title="Mix", entries=("https://y/watch?v=p1", "https://y/watch?v=p2"))
        return VideoInfo(
            url=url,
            id="abcdefghijk",
            title=f"Title of {url.rsplit('=', 1)[-1]}",
            uploader="Someone",
            duration=75,
            tracks=SubtitleTracks(manual=("en",), automatic=("en", "ja")),
        )


@pytest.fixture
def downloads() -> FakeDownloads:
    return FakeDownloads()


@pytest.fixture
def manager(downloads):
    instance = JobManager(downloads.download, downloads.probe)
    yield instance
    downloads.hold.set()
    instance.shutdown(2.0)


class Client:
    """A tiny browser: remembers the cookie and speaks JSON."""

    def __init__(self, server: UiServer) -> None:
        self.server = server
        self.port = server.port
        self.cookie = f"{server.cookie_name}={server.app.token}"

    def request(self, method, path, body=None, cookie=True, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        sent = {"Host": f"127.0.0.1:{self.port}"}
        if cookie:
            sent["Cookie"] = self.cookie if cookie is True else cookie
        payload = None
        if method == "POST":
            sent["Content-Type"] = "application/json"
            payload = json.dumps({} if body is None else body)
        sent.update(headers or {})
        connection.request(method, path, body=payload, headers=sent)
        response = connection.getresponse()
        raw = response.read()
        connection.close()
        return response, raw

    def get(self, path, **kwargs):
        response, raw = self.request("GET", path, **kwargs)
        return response.status, json.loads(raw) if "json" in response.headers.get("Content-Type", "") else raw

    def post(self, path, body=None, **kwargs):
        response, raw = self.request("POST", path, body, **kwargs)
        return response.status, json.loads(raw) if "json" in response.headers.get("Content-Type", "") else raw


@pytest.fixture
def ui(tmp_path, manager):
    """A real server on a free port, with the fake downloads behind it."""
    app = App(Options(output=str(tmp_path / "out")), manager=manager)
    server = UiServer(("127.0.0.1", 0), app)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    thread.start()
    yield Client(server)
    app.stop.set()
    server.shutdown()
    server.server_close()


@pytest.fixture
def out_dir(tmp_path) -> Path:
    return tmp_path / "out"
