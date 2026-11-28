"""Starting and stopping the UI: one server per user, found again by a second `yt`."""

import http.client
import json
import os
import socket
import sys
import threading
import time
from contextlib import closing
from urllib.parse import parse_qs, urlsplit

import pytest

from ytcli.models import AppError
from ytcli.settings import Options, config_path
from ytcli.ui import web
from ytcli.ui.web import system
from ytcli.ui.web.app import App
from ytcli.ui.web.server import cookie_name

from .conftest import wait_until


@pytest.fixture
def running(tmp_path):
    """Run the real `run_ui` in a thread and hand back how it was reached."""
    started: dict = {"lines": []}
    ready = threading.Event()

    def note(url):
        started["url"] = url
        ready.set()

    def serve(options=None, **kwargs):
        started["code"] = web.run_ui(
            options or Options(output=str(tmp_path / "out")),
            announce=started["lines"].append,
            ready=note,
            **kwargs,
        )

    def start(**kwargs):
        thread = threading.Thread(target=serve, kwargs=kwargs, daemon=True)
        thread.start()
        started["thread"] = thread
        assert ready.wait(5)
        return started

    yield start
    if "thread" in started and started["thread"].is_alive():
        quit_ui(started["url"])
        started["thread"].join(5)


def request_ui(url, method, path):
    address = urlsplit(url)
    token = parse_qs(address.query)["k"][0]
    headers = {"Cookie": f"{cookie_name(address.port)}={token}", "Content-Type": "application/json"}
    with closing(http.client.HTTPConnection(address.hostname, address.port, timeout=5)) as connection:
        connection.request(method, path, body="{}" if method == "POST" else None, headers=headers)
        response = connection.getresponse()
        assert response.status == 200
        return json.loads(response.read())


def quit_ui(url: str) -> None:
    request_ui(url, "POST", "/api/quit")


def test_it_serves_opens_the_browser_and_stops_on_quit(running, desktop):
    started = running(port=0)
    url = started["url"]

    assert url.startswith("http://127.0.0.1:") and "/?k=" in url
    assert desktop["browser"] == [url]
    assert any(url in line for line in started["lines"])
    assert web.running_url(web.load_session()) == url

    quit_ui(url)
    started["thread"].join(5)
    assert not started["thread"].is_alive()
    assert started["code"] == 0
    assert web.load_session()["port"] == 0
    assert web.running_url(web.load_session()) is None


def test_a_second_yt_reopens_the_running_one(running, desktop):
    url = running(port=0)["url"]
    lines: list[str] = []

    assert web.run_ui(Options(), announce=lines.append) == 0

    assert desktop["browser"] == [url, url]
    assert lines == [f"yt UI is already running: {url}"]


@pytest.mark.parametrize("use_default", [True, False])
def test_startup_shows_the_effective_folder(running, monkeypatch, tmp_path, use_default):
    monkeypatch.setattr(system, "downloads_dir", lambda: tmp_path / "Downloads")
    chosen = Options() if use_default else Options(output=str(tmp_path / "music"))
    url = running(options=chosen, port=0)["url"]
    state = request_ui(url, "GET", "/api/state")
    assert state["folder"] == str(tmp_path / ("Downloads" if use_default else "music"))
    request_ui(url, "POST", "/api/settings")
    assert Options.load().output == chosen.output


def test_no_open_leaves_the_browser_alone(running, desktop):
    running(port=0, open_browser=False)
    assert desktop["browser"] == []


def test_a_missing_browser_is_explained(running, monkeypatch):
    monkeypatch.setattr(system, "open_browser", lambda url: False)
    started = running(port=0)
    assert "Could not open a browser. Open the address above yourself." in started["lines"]


def test_it_leaves_once_nobody_is_looking(running):
    started = running(port=0, linger=0.05)
    started["thread"].join(5)
    assert not started["thread"].is_alive()
    assert "No tab is open any more: stopping." in started["lines"]


def test_the_secret_survives_a_restart_so_old_tabs_keep_working(running):
    first = running(port=0)
    token = first["url"].split("k=")[1]
    quit_ui(first["url"])
    first["thread"].join(5)
    assert web.load_session()["token"] == token


class TestSession:
    def test_a_fresh_secret_when_there_is_no_file(self):
        first, second = web.load_session(), web.load_session()
        assert first["port"] == 0 and len(first["token"]) >= 24
        assert first["token"] != second["token"]

    def test_round_trip(self):
        web.save_session({"token": "t" * 32, "port": 4816})
        assert web.load_session() == {"token": "t" * 32, "port": 4816}
        assert web.session_path() == config_path().parent / "ui.json"

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
    def test_only_the_user_can_read_the_secret(self):
        web.save_session({"token": "t" * 32, "port": 1})
        assert os.stat(web.session_path()).st_mode & 0o777 == 0o600

    @pytest.mark.parametrize(
        "content", ["", "not json", "[]", '{"token": "short", "port": 1}', '{"token": 5}']
    )
    def test_a_damaged_file_is_replaced_by_a_fresh_secret(self, content):
        web.session_path().parent.mkdir(parents=True, exist_ok=True)
        web.session_path().write_text(content)
        assert web.load_session()["port"] == 0

    def test_a_stale_port_is_not_mistaken_for_a_running_ui(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            free_port = probe.getsockname()[1]
        assert web.running_url({"token": "t" * 32, "port": free_port}) is None

    def test_another_program_on_the_port_is_not_ours(self):
        with socket.socket() as other:
            other.bind(("127.0.0.1", 0))
            other.listen(1)
            other.settimeout(0.01)
            assert web.running_url({"token": "t" * 32, "port": other.getsockname()[1]}) is None


class TestBinding:
    def test_starting_never_waits_for_a_name_lookup(self, manager, monkeypatch):
        def slow_lookup(*_args):
            raise AssertionError("the server must not look its own name up")

        monkeypatch.setattr(socket, "getfqdn", slow_lookup)
        server = web.bind(App(Options(), manager=manager), 0)
        try:
            assert (server.server_name, server.server_port) == ("127.0.0.1", server.port)
        finally:
            server.server_close()

    def test_an_explicit_port_that_is_taken_is_an_error(self, manager):
        with socket.socket() as other:
            other.bind(("127.0.0.1", 0))
            other.listen(1)
            with pytest.raises(AppError, match="Could not use port"):
                web.bind(App(Options(), manager=manager), other.getsockname()[1])

    def test_the_usual_port_falls_back_to_a_free_one(self, manager, monkeypatch):
        with socket.socket() as other:
            other.bind(("127.0.0.1", 0))
            other.listen(1)
            taken = other.getsockname()[1]
            monkeypatch.setattr(web, "DEFAULT_PORT", taken)
            server = web.bind(App(Options(), manager=manager), None)
            try:
                assert server.port not in (0, taken)
            finally:
                server.server_close()


class TestAbandoned:
    def app(self, manager, linger):
        return App(Options(), manager=manager, linger=linger)

    def test_a_terminal_session_never_leaves_by_itself(self, manager):
        assert self.app(manager, None).abandoned() is False

    def test_it_waits_out_the_grace_period(self, manager):
        app = self.app(manager, 0.03)
        assert app.abandoned() is False
        time.sleep(0.05)
        assert app.abandoned() is True

    def test_an_open_tab_keeps_it_alive(self, manager):
        app = self.app(manager, 0.0)
        app.tab_opened()
        time.sleep(0.01)
        assert app.abandoned() is False
        app.tab_closed()
        time.sleep(0.01)
        assert app.abandoned() is True

    def test_a_running_download_keeps_it_alive(self, manager, downloads, tmp_path):
        downloads.hold.clear()
        app = self.app(manager, 0.0)
        manager.submit(["https://y/watch?v=one"], Options(output=str(tmp_path)))
        time.sleep(0.01)
        assert app.abandoned() is False
        downloads.hold.set()
        wait_until(lambda: not manager.active())
        time.sleep(0.01)
        assert app.abandoned() is True


def test_the_session_file_is_plain_json():
    web.save_session({"token": "t" * 32, "port": 7})
    assert json.loads(web.session_path().read_text()) == {"token": "t" * 32, "port": 7}
