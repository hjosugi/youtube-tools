#!/usr/bin/env python3
"""Set the version of `yt` in every file that records it, and print the new one.

python scripts/bump-version.py            # patch: 1.1.0 -> 1.1.1
python scripts/bump-version.py minor      # 1.1.0 -> 1.2.0
python scripts/bump-version.py major      # 1.1.0 -> 2.0.0
python scripts/bump-version.py 1.4.2      # exactly this
python scripts/bump-version.py --show     # print the current version, change nothing

Standard library only: the release workflow runs this with a token that can push, so it
must not pull code from anywhere.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "apps" / "yt"

# (file, text before the version, text after it)
PLACES = (
    (APP / "ytcli" / "__init__.py", '__version__ = "', '"'),
    (APP / "pyproject.toml", '[project]\nname = "yt-tools"\nversion = "', '"'),
    (APP / "uv.lock", '[[package]]\nname = "yt-tools"\nversion = "', '"'),
)
VERSION_RE = re.compile(r"\d+\.\d+\.\d+")


def current_version() -> str:
    path, before, _after = PLACES[0]
    found = re.search(re.escape(before) + f"({VERSION_RE.pattern})", path.read_text(encoding="utf-8"))
    if not found:
        raise SystemExit(f"error: no version found in {path}")
    return found.group(1)


def next_version(current: str, request: str) -> str:
    if VERSION_RE.fullmatch(request):
        return request
    major, minor, patch = (int(part) for part in current.split("."))
    if request == "major":
        return f"{major + 1}.0.0"
    if request == "minor":
        return f"{major}.{minor + 1}.0"
    if request == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise SystemExit(f"error: expected patch, minor, major or X.Y.Z, got {request!r}")


def main() -> int:
    request = sys.argv[1] if len(sys.argv) > 1 else "patch"
    current = current_version()
    if request == "--show":
        print(current)
        return 0
    new = next_version(current, request)
    for path, before, after in PLACES:
        text = path.read_text(encoding="utf-8")
        old = f"{before}{current}{after}"
        if text.count(old) != 1:
            raise SystemExit(f"error: expected exactly one {current} version line in {path}")
        path.write_text(text.replace(old, f"{before}{new}{after}"), encoding="utf-8", newline="\n")
    print(new)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
