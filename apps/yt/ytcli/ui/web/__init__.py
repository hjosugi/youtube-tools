"""The local web UI: `yt` starts a small server on 127.0.0.1 and opens it in the browser.

The page only collects a URL and a button press; the same download code as the command
line does the work, in this process.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
import urllib.request
from collections.abc import Callable
from pathlib import Path

from ... import __version__
from ...models import AppError
from ...settings import Options, config_path
from . import system
from .app import App
from .server import HOST, UiServer, cookie_name, start_url

__all__ = ["run_ui"]

DEFAULT_PORT = 4816
SESSION_FILENAME = "ui.json"
POLL_SECONDS = 0.5


def run_ui(
    options: Options,
    port: int | None = None,
    open_browser: bool = True,
    linger: float | None = None,
    announce: Callable[[str], None] | None = None,
    ready: Callable[[str], None] | None = None,
) -> int:
    """Serve the UI until it is quit, interrupted or left alone for `linger` seconds."""
    announce = announce or say
    system.restore_library_path()
    session = load_session()

    running = running_url(session)
    if running:
        # A second `yt` only brings the existing window back instead of starting a twin.
        announce(f"yt UI is already running: {running}")
        if open_browser:
            system.open_browser(running)
        return 0

    app = App(options, token=session["token"], linger=linger)
    server = bind(app, port)
    save_session({"token": app.token, "port": server.port})
    url = start_url(server.port, app.token)

    thread = threading.Thread(target=server.serve_forever, daemon=True, name="yt-http")
    thread.start()
    announce(f"yt {__version__} UI: {url}")
    announce("Close this with Ctrl+C or the Quit button in the page.")
    if open_browser and not system.open_browser(url):
        announce("Could not open a browser. Open the address above yourself.")
    if ready is not None:
        ready(url)

    try:
        while not app.stop.wait(POLL_SECONDS):
            if app.abandoned():
                announce("No tab is open any more: stopping.")
                break
    except KeyboardInterrupt:
        announce("")
    finally:
        app.stop.set()
        app.manager.shutdown()
        server.shutdown()
        server.server_close()
        save_session({"token": app.token, "port": 0})
    return 0


def say(line: str) -> None:
    """Print at once: a launcher or a pipe reading our output must see the address now."""
    print(line, flush=True)


def bind(app: App, port: int | None) -> UiServer:
    """Listen on the requested port, or on our usual one, or on any free one."""
    if port is not None:
        try:
            return UiServer((HOST, port), app)
        except OSError as error:
            raise AppError(f"Could not use port {port}: {error}") from error
    try:
        return UiServer((HOST, DEFAULT_PORT), app)
    except OSError:
        return UiServer((HOST, 0), app)


# ---- the session file: one secret per user, and where a running server listens ----------


def session_path() -> Path:
    return config_path().parent / SESSION_FILENAME


def load_session() -> dict:
    """The stored secret and port, or a fresh secret when there is no usable file."""
    try:
        stored = json.loads(session_path().read_text(encoding="utf-8"))
        token, port = stored["token"], stored["port"]
        if isinstance(token, str) and len(token) >= 16 and isinstance(port, int):
            return {"token": token, "port": port}
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return {"token": secrets.token_urlsafe(24), "port": 0}


def save_session(session: dict) -> None:
    """Keep the secret readable by this user only; it is what lets a browser in."""
    path = session_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(session, handle)
    except OSError:
        pass  # without the file the UI still works, a second `yt` just cannot find it


def running_url(session: dict) -> str | None:
    """The address of a UI server that is already up for this user, if any."""
    port = session.get("port")
    if not port:
        return None
    request = urllib.request.Request(
        f"http://{HOST}:{port}/api/ping", headers={"Cookie": f"{cookie_name(port)}={session['token']}"}
    )
    # No proxies: an http_proxy setting must never see a request meant for this machine.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=1.0) as response:
            if json.load(response).get("app") == "yt":
                return start_url(port, session["token"])
    except (OSError, ValueError):
        pass
    return None
