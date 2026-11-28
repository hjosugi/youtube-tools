"""Check that a built `yt` binary really works: version, then the web UI end to end.

uv run python smoke.py dist/yt-linux-x86_64

A frozen binary can pass `--version` and still be missing the UI's page files or fail to
start its server, so this starts the UI, loads the page and its assets, and quits it.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    binary = str(Path(sys.argv[1]).resolve())

    version = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=120)
    print(version.stdout.strip() or version.stderr.strip())
    if version.returncode != 0 or not version.stdout.startswith("yt "):
        return fail("--version did not answer")

    scripts = Path(__file__).resolve().parent / "ytcli" / "completions"
    for shell, filename in (("bash", "yt.bash"), ("zsh", "yt.zsh"), ("fish", "yt.fish"), ("pwsh", "yt.ps1")):
        script = subprocess.run([binary, "-c", shell], capture_output=True, text=True, timeout=120)
        if script.returncode != 0 or script.stdout != (scripts / filename).read_text(encoding="utf-8"):
            return fail(f"the embedded {shell} completion differs from {filename}")

    with tempfile.TemporaryDirectory() as scratch:
        environment = os.environ | {
            "YT_CONFIG_FILE": str(Path(scratch) / "config.toml"),
            "YT_CACHE_DIR": str(Path(scratch) / "cache"),
        }
        process = subprocess.Popen(
            [binary, "ui", "--no-open", "--port", "0", "-o", scratch],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=environment,
        )
        try:
            line = process.stdout.readline()
            found = re.search(r"http://127\.0\.0\.1:(\d+)/\?k=(\S+)", line)
            if not found:
                return fail(f"the UI did not print its address: {line!r}")
            port, token = int(found.group(1)), found.group(2)
            check_ui(port, token)
            request(port, token, "POST", "/api/quit")
            code = process.wait(timeout=30)
            if code != 0:
                return fail(f"the UI exited with {code}")
        finally:
            if process.poll() is None:
                process.kill()
    print("smoke test passed")
    return 0


def check_ui(port: int, token: str) -> None:
    status, page = request(port, token, "GET", f"/?k={token}")
    assert status == 200 and b"<title>yt</title>" in page, "the page is missing"
    for asset in ("app.js", "style.css", "icon.svg"):
        status, body = request(port, token, "GET", f"/assets/{asset}")
        assert status == 200 and body, f"{asset} is missing from the binary"
    status, body = request(port, token, "GET", "/api/state")
    state = json.loads(body)
    assert status == 200 and state["version"], "the state endpoint is broken"
    print(f"UI ok on port {port}: version {state['version']}, ffmpeg {state['ffmpeg']}")


def request(port: int, token: str, method: str, path: str) -> tuple[int, bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    headers = {"Cookie": f"yt_{port}={token}"}
    body = None
    if method == "POST":
        headers["Content-Type"] = "application/json"
        body = "{}"
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return response.status, data


def fail(message: str) -> int:
    print(f"smoke test failed: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
