"""The HTTP side of the web UI: standard library only, bound to 127.0.0.1.

A local server that writes files and opens folders must not be drivable by whatever web
page happens to be open in the same browser, so every request has to
  * name us in its Host header (stops DNS rebinding),
  * carry the session cookie, which is only handed out for the secret in the start URL,
  * and, for anything that changes state, be same-origin JSON (stops cross-site forms).
"""

from __future__ import annotations

import json
import re
import secrets
import sys
import threading
import time
from dataclasses import replace
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import parse_qs, urlsplit

from ... import __version__, ffmpeg
from ...models import AUDIO_FORMATS, AUDIO_QUALITIES, VIDEO_FORMATS, VIDEO_QUALITIES, AppError
from ...modes import parse_modes
from ...settings import DEFAULTS, Options, config_path, save_config
from ...subtitles import SUBTITLE_FORMATS
from . import system
from .jobs import JobManager

HOST = "127.0.0.1"
MAX_BODY = 256 * 1024
MAX_URLS = 200
EVENT_INTERVAL = 0.15  # seconds between two pushes, so fast progress cannot flood the page
HEARTBEAT = 10.0  # seconds between keep-alives, which is also how fast a closed tab is noticed

ASSETS = {
    "app.js": "text/javascript; charset=utf-8",
    "style.css": "text/css; charset=utf-8",
    "icon.svg": "image/svg+xml",
}
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' https://i.ytimg.com; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cache-Control": "no-store",
}
LOCKED_OUT = """<!doctype html><meta charset="utf-8"><title>yt</title>
<body style="font-family:system-ui;max-width:32rem;margin:4rem auto;line-height:1.7">
<h1>yt</h1>
<p>This page only opens from the link <code>yt</code> prints when it starts.
Run <code>yt</code> again and use the tab it opens.</p>
<p>このページは <code>yt</code> の起動時に開くリンクからのみ表示できます。
もう一度 <code>yt</code> を起動してください。</p>
"""

ROUTES: tuple[tuple[str, re.Pattern[str], str], ...] = tuple(
    (method, re.compile(pattern), name)
    for method, pattern, name in (
        ("GET", r"/", "page"),
        ("GET", r"/assets/(?P<name>[\w.-]+)", "asset"),
        ("GET", r"/api/ping", "ping"),
        ("GET", r"/api/state", "state"),
        ("GET", r"/api/events", "events"),
        ("GET", r"/api/folders", "folders"),
        ("GET", r"/api/jobs/(?P<job>\d+)/log", "job_log"),
        ("POST", r"/api/info", "info"),
        ("POST", r"/api/jobs", "submit"),
        ("POST", r"/api/jobs/clear", "clear"),
        ("POST", r"/api/jobs/(?P<job>\d+)/cancel", "cancel"),
        ("POST", r"/api/settings", "settings"),
        ("POST", r"/api/open", "open"),
        ("POST", r"/api/quit", "quit"),
    )
)


class App:
    """Everything the handlers share: the current settings, the queue and who is watching."""

    def __init__(
        self,
        options: Options,
        token: str | None = None,
        manager: JobManager | None = None,
        linger: float | None = None,
    ) -> None:
        self.options = options
        self.token = token or secrets.token_urlsafe(24)
        self.manager = manager or JobManager()
        self.linger = linger
        self.stop = threading.Event()
        self._lock = threading.Lock()
        self._clients = 0
        self._last_seen = time.monotonic()

    def client_connected(self) -> None:
        with self._lock:
            self._clients += 1

    def client_gone(self) -> None:
        with self._lock:
            self._clients -= 1
            self._last_seen = time.monotonic()

    def abandoned(self) -> bool:
        """True once no tab has been open for `linger` seconds and nothing is downloading."""
        if self.linger is None:
            return False
        with self._lock:
            if self._clients:
                return False
            idle = time.monotonic() - self._last_seen
        if self.manager.active():
            with self._lock:
                self._last_seen = time.monotonic()
            return False
        return idle > self.linger

    def state(self) -> dict:
        """What the page needs to draw itself from scratch."""
        _revision, jobs = self.manager.snapshot()
        return {
            "version": __version__,
            "options": self.options.to_config(),
            "folder": str(self.options.out_dir),
            "folder_label": system.short_path(self.options.out_dir),
            "choices": {
                "video_quality": VIDEO_QUALITIES,
                "video_format": VIDEO_FORMATS,
                "audio_quality": AUDIO_QUALITIES,
                "audio_format": AUDIO_FORMATS,
                "sub_formats": SUBTITLE_FORMATS,
            },
            "ffmpeg": ffmpeg.status(),
            "first_run": not config_path().is_file(),
            "jobs": jobs,
        }

    def update_options(self, changes: dict) -> None:
        """Apply settings sent by the page and remember them as the new defaults."""
        merged = self.options.to_config()
        for key, value in changes.items():
            if key not in DEFAULTS:
                continue
            if isinstance(DEFAULTS[key], bool):
                if not isinstance(value, bool):
                    raise AppError(f"{key} must be true or false.")
                merged[key] = value
            elif isinstance(value, list | tuple):
                merged[key] = ",".join(str(item) for item in value)
            elif isinstance(value, str):
                merged[key] = value.strip()
            else:
                raise AppError(f"{key} must be text.")
        if not merged["output"]:
            raise AppError("Choose a folder to save to.")
        updated = Options.from_config(merged)
        updated.insecure = self.options.insecure
        save_config(updated.to_config())
        self.options = updated


class UiServer(ThreadingHTTPServer):
    """One thread per request, so a long event stream never blocks a button press."""

    daemon_threads = True
    # On Windows SO_REUSEADDR would let a second copy bind the very same port.
    allow_reuse_address = sys.platform != "win32"

    def __init__(self, address: tuple[str, int], app: App) -> None:
        super().__init__(address, Handler)
        self.app = app

    @property
    def port(self) -> int:
        return self.server_address[1]

    @property
    def cookie_name(self) -> str:
        # Cookies are shared between ports of one host, so the port is part of the name.
        return f"yt_{self.port}"


class Handler(BaseHTTPRequestHandler):
    server: UiServer
    protocol_version = "HTTP/1.1"
    server_version = "yt"
    sys_version = ""

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - name set by the base class
        """Stay quiet: the terminal that started us is not an access log."""

    def do_GET(self) -> None:  # noqa: N802 - name set by the base class
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802 - name set by the base class
        self._dispatch("POST")

    # ---- plumbing --------------------------------------------------------------------

    def _dispatch(self, method: str) -> None:
        url = urlsplit(self.path)
        self.query = parse_qs(url.query)
        try:
            if not self._host_is_ours():
                return self._refuse(b"forbidden", "text/plain")
            fresh_login = method == "GET" and url.path == "/" and self._has_start_key()
            if not (fresh_login or self._has_cookie()):
                return self._refuse(LOCKED_OUT.encode(), "text/html; charset=utf-8")
            if method == "POST" and not self._is_same_origin_json():
                return self._refuse(b"forbidden", "text/plain")
            for route_method, pattern, name in ROUTES:
                match = pattern.fullmatch(url.path)
                if match and route_method == method:
                    return getattr(self, f"_route_{name}")(**match.groupdict())
            self.close_connection = True
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except AppError as error:
            self.close_connection = True  # the request body may not have been read
            self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except (BrokenPipeError, ConnectionError):
            self.close_connection = True  # the tab went away mid-answer
        except Exception as error:  # a handler bug must not take the server down
            self._json({"error": f"unexpected error: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _refuse(self, body: bytes, content_type: str) -> None:
        """Answer 403 and drop the connection, since any request body was left unread."""
        self.close_connection = True
        self._send(HTTPStatus.FORBIDDEN, body, content_type)

    def _host_is_ours(self) -> bool:
        port = self.server.port
        return self.headers.get("Host", "") in {f"{HOST}:{port}", f"localhost:{port}"}

    def _has_start_key(self) -> bool:
        key = (self.query.get("k") or [""])[0]
        return secrets.compare_digest(key.encode(), self.server.app.token.encode())

    def _has_cookie(self) -> bool:
        wanted = f"{self.server.cookie_name}={self.server.app.token}".encode()
        return any(
            secrets.compare_digest(part.strip().encode(), wanted)
            for part in self.headers.get("Cookie", "").split(";")
        )

    def _is_same_origin_json(self) -> bool:
        origin = self.headers.get("Origin")
        port = self.server.port
        if origin is not None and origin not in {f"http://{HOST}:{port}", f"http://localhost:{port}"}:
            return False
        return self.headers.get("Content-Type", "").split(";")[0].strip() == "application/json"

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise AppError("Request too large.")
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError as error:
            raise AppError("Request is not valid JSON.") from error
        if not isinstance(body, dict):
            raise AppError("Request must be a JSON object.")
        return body

    def _send(self, status: int, body: bytes, content_type: str, cookie: bool = False) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        if cookie:
            self.send_header(
                "Set-Cookie",
                f"{self.server.cookie_name}={self.server.app.token}; Path=/; HttpOnly; SameSite=Strict",
            )
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        self._send(status, json.dumps(payload).encode(), "application/json")

    # ---- pages -----------------------------------------------------------------------

    def _route_page(self) -> None:
        # Served together with the cookie, so the secret in the URL is needed only once.
        self._send(HTTPStatus.OK, _asset("index.html"), "text/html; charset=utf-8", cookie=True)

    def _route_asset(self, name: str) -> None:
        if name not in ASSETS:
            return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        self._send(HTTPStatus.OK, _asset(name), ASSETS[name])

    # ---- reading ---------------------------------------------------------------------

    def _route_ping(self) -> None:
        self._json({"app": "yt", "version": __version__})

    def _route_state(self) -> None:
        self._json(self.server.app.state())

    def _route_folders(self) -> None:
        self._json(system.list_folders((self.query.get("path") or [""])[0]))

    def _route_job_log(self, job: str) -> None:
        lines = self.server.app.manager.log_lines(job)
        if lines is None:
            return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        self._json({"lines": lines})

    def _route_events(self) -> None:
        """Server-sent events: the job list, pushed whenever it changes."""
        app = self.server.app
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

        app.client_connected()
        revision = -1
        try:
            while not app.stop.is_set():
                current, jobs = app.manager.snapshot()
                if current != revision:
                    revision = current
                    self.wfile.write(f"event: jobs\ndata: {json.dumps({'jobs': jobs})}\n\n".encode())
                    self.wfile.flush()
                    time.sleep(EVENT_INTERVAL)
                elif app.manager.wait(revision, HEARTBEAT) == revision:
                    self.wfile.write(b": still here\n\n")
                    self.wfile.flush()
        except OSError:
            pass  # the tab was closed
        finally:
            app.client_gone()

    # ---- doing -----------------------------------------------------------------------

    def _route_info(self) -> None:
        app = self.server.app
        url = _clean_urls([self._body().get("url")])[0]
        found = app.manager.info(url, app.options.insecure)
        self._json(
            {
                "url": url,
                "id": found.id,
                "title": found.title,
                "uploader": found.uploader,
                "duration": found.duration,
                "manual": found.tracks.manual,
                "automatic": found.tracks.automatic,
                "playlist": len(found.entries),
            }
        )

    def _route_submit(self) -> None:
        app = self.server.app
        body = self._body()
        urls = _clean_urls(body.get("urls"))
        modes = parse_modes(str(body.get("mode") or app.options.modes))
        # The button pressed last becomes the default one, so Enter repeats it next time.
        app.options = replace(app.options, modes=modes)
        save_config(app.options.to_config())
        jobs = app.manager.submit(urls, app.options)
        self._json({"jobs": [job.id for job in jobs]})

    def _route_clear(self) -> None:
        self.server.app.manager.clear()
        self._json({"ok": True})

    def _route_cancel(self, job: str) -> None:
        self._json({"ok": self.server.app.manager.cancel(job)})

    def _route_settings(self) -> None:
        app = self.server.app
        app.update_options(self._body())
        self._json(app.state())

    def _route_open(self) -> None:
        """Open the output folder, or a finished file, picked from what the server knows."""
        app = self.server.app
        body = self._body()
        if body.get("job") is None:
            target = app.options.out_dir
            target.mkdir(parents=True, exist_ok=True)
        else:
            job = app.manager.get(str(body["job"]))
            if job is None:
                raise AppError("That download is no longer in the list.")
            index = body.get("file")
            if index is None:
                target = job.options.out_dir
            elif isinstance(index, int) and 0 <= index < len(job.files):
                target = job.files[index]
            else:
                raise AppError("No such file.")
        system.open_path(target)
        self._json({"ok": True})

    def _route_quit(self) -> None:
        self._json({"ok": True})
        self.server.app.stop.set()


def _asset(name: str) -> bytes:
    return resources.files(__package__).joinpath("static", name).read_bytes()


def _clean_urls(raw) -> list[str]:
    """Accept only web links; this is the one place user text becomes a URL for yt-dlp."""
    if not isinstance(raw, list):
        raise AppError("Enter a YouTube URL.")
    urls = list(dict.fromkeys(item.strip() for item in raw if isinstance(item, str) and item.strip()))
    if not urls:
        raise AppError("Enter a YouTube URL.")
    if len(urls) > MAX_URLS:
        raise AppError(f"Too many URLs at once (the limit is {MAX_URLS}).")
    for url in urls:
        if not re.fullmatch(r"https?://\S+", url):
            raise AppError(f"Not a web address: {url}")
    return urls
