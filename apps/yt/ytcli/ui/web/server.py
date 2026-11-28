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
import socketserver
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import parse_qs, urlsplit

from ... import __version__
from ...models import AppError
from . import system
from .app import App

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


def start_url(port: int, token: str) -> str:
    """The link that lets a browser in: the page, with the secret that buys the cookie."""
    return f"http://{HOST}:{port}/?k={token}"


def cookie_name(port: int) -> str:
    """Cookies are shared between the ports of one host, so the port is part of the name."""
    return f"yt_{port}"


class UiServer(ThreadingHTTPServer):
    """One thread per request, so a long event stream never blocks a button press."""

    daemon_threads = True
    # On Windows SO_REUSEADDR would let a second copy bind the very same port.
    allow_reuse_address = sys.platform != "win32"

    def __init__(self, address: tuple[str, int], app: App) -> None:
        super().__init__(address, Handler)
        self.app = app

    def server_bind(self) -> None:
        """Bind without HTTPServer's reverse lookup of our own address.

        The stock method calls socket.getfqdn(), which takes several seconds on some Macs,
        only to fill in a server name that nothing here reads.
        """
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]

    @property
    def port(self) -> int:
        return self.server_address[1]

    @property
    def hosts(self) -> tuple[str, str]:
        """The two spellings of our own address a browser may use."""
        return f"{HOST}:{self.port}", f"localhost:{self.port}"


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
            if self.headers.get("Host", "") not in self.server.hosts:
                return self._refuse(b"forbidden", "text/plain")
            fresh_login = method == "GET" and url.path == "/" and self._has_start_key()
            if not (fresh_login or self._has_cookie()):
                return self._refuse(LOCKED_OUT.encode(), "text/html; charset=utf-8")
            if method == "POST" and not self._is_same_origin_json():
                return self._refuse(b"forbidden", "text/plain")
            for route_method, pattern, route in ROUTES:
                match = pattern.fullmatch(url.path)
                if match and route_method == method:
                    # Browsers reuse this connection even when the handler ignores its JSON.
                    if method == "POST":
                        return route(self, self._body(), **match.groupdict())
                    return route(self, **match.groupdict())
            self._not_found()
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

    def _not_found(self) -> None:
        self.close_connection = True
        self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def _cookie(self) -> str:
        return f"{cookie_name(self.server.port)}={self.server.app.token}"

    def _has_start_key(self) -> bool:
        return secrets.compare_digest(self._query("k").encode(), self.server.app.token.encode())

    def _has_cookie(self) -> bool:
        wanted = self._cookie().encode()
        return any(
            secrets.compare_digest(part.strip().encode(), wanted)
            for part in self.headers.get("Cookie", "").split(";")
        )

    def _is_same_origin_json(self) -> bool:
        origin = self.headers.get("Origin")
        if origin is not None and origin not in {f"http://{host}" for host in self.server.hosts}:
            return False
        return self.headers.get("Content-Type", "").split(";")[0].strip() == "application/json"

    def _query(self, name: str) -> str:
        """One query parameter, or an empty string."""
        return (self.query.get(name) or [""])[0]

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length < 0:
                raise ValueError
        except ValueError as error:
            raise AppError("Invalid Content-Length.") from error
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
            self.send_header("Set-Cookie", f"{self._cookie()}; Path=/; HttpOnly; SameSite=Strict")
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
            return self._not_found()
        self._send(HTTPStatus.OK, _asset(name), ASSETS[name])

    # ---- reading ---------------------------------------------------------------------

    def _route_ping(self) -> None:
        self._json({"app": "yt", "version": __version__})

    def _route_state(self) -> None:
        self._json(self.server.app.state())

    def _route_folders(self) -> None:
        self._json(system.list_folders(self._query("path")))

    def _route_job_log(self, job: str) -> None:
        lines = self.server.app.manager.log_lines(job)
        if lines is None:
            return self._not_found()
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

        app.tab_opened()
        revision = -1  # no real revision is negative, so the first wait returns at once
        try:
            while not app.stop.is_set():
                if app.manager.wait(revision, HEARTBEAT) == revision:
                    self.wfile.write(b": still here\n\n")
                    self.wfile.flush()
                    continue
                revision, jobs = app.manager.snapshot()
                self.wfile.write(f"event: jobs\ndata: {json.dumps({'jobs': jobs})}\n\n".encode())
                self.wfile.flush()
                time.sleep(EVENT_INTERVAL)
        except OSError:
            pass  # the tab was closed
        finally:
            app.tab_closed()

    # ---- doing -----------------------------------------------------------------------

    def _route_info(self, body: dict) -> None:
        app = self.server.app
        url = _clean_urls([body.get("url")])[0]
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

    def _route_submit(self, body: dict) -> None:
        jobs = self.server.app.submit(_clean_urls(body.get("urls")), str(body.get("mode") or ""))
        self._json({"jobs": [job.id for job in jobs]})

    def _route_clear(self, _body: dict) -> None:
        self.server.app.manager.clear()
        self._json({"ok": True})

    def _route_cancel(self, _body: dict, job: str) -> None:
        self._json({"ok": self.server.app.manager.cancel(job)})

    def _route_settings(self, body: dict) -> None:
        app = self.server.app
        app.update_options(body)
        self._json(app.state())

    def _route_open(self, body: dict) -> None:
        """Open the output folder, or a finished file, picked from what the server knows."""
        app = self.server.app
        if body.get("job") is None:
            target = app.current.out_dir
            target.mkdir(parents=True, exist_ok=True)
        else:
            job = app.manager.get(str(body["job"]))
            if job is None:
                raise AppError("That download is no longer in the list.")
            index = body.get("file")
            if index is None:
                target = job.folder
            elif isinstance(index, int) and 0 <= index < len(job.files):
                target = job.files[index].path
            else:
                raise AppError("No such file.")
        system.open_path(target)
        self._json({"ok": True})

    def _route_quit(self, _body: dict) -> None:
        self._json({"ok": True})
        self.server.app.stop.set()


# Checked in order; a named group becomes the handler's argument.
ROUTES = tuple(
    (method, re.compile(pattern), route)
    for method, pattern, route in (
        ("GET", r"/", Handler._route_page),
        ("GET", r"/assets/(?P<name>[\w.-]+)", Handler._route_asset),
        ("GET", r"/api/ping", Handler._route_ping),
        ("GET", r"/api/state", Handler._route_state),
        ("GET", r"/api/events", Handler._route_events),
        ("GET", r"/api/folders", Handler._route_folders),
        ("GET", r"/api/jobs/(?P<job>\d+)/log", Handler._route_job_log),
        ("POST", r"/api/info", Handler._route_info),
        ("POST", r"/api/jobs", Handler._route_submit),
        ("POST", r"/api/jobs/clear", Handler._route_clear),
        ("POST", r"/api/jobs/(?P<job>\d+)/cancel", Handler._route_cancel),
        ("POST", r"/api/settings", Handler._route_settings),
        ("POST", r"/api/open", Handler._route_open),
        ("POST", r"/api/quit", Handler._route_quit),
    )
)


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
