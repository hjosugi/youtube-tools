"""The few things the web UI asks of the desktop: a browser tab, a file manager, folders."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import webbrowser
from pathlib import Path

from ...models import AppError

USER_DIRS_RE = re.compile(r'^XDG_DOWNLOAD_DIR="(?P<path>.+)"\s*$', re.MULTILINE)


def restore_library_path() -> None:
    """Undo PyInstaller's library path so the browser and file manager we start still work.

    The frozen binary runs with LD_LIBRARY_PATH pointing at its own bundled libraries.
    Programs we launch would inherit that and load our copies instead of the system's.
    """
    if not getattr(sys, "frozen", False):
        return
    for key in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
        original = os.environ.get(f"{key}_ORIG")
        if original is not None:
            os.environ[key] = original
        else:
            os.environ.pop(key, None)


def open_browser(url: str) -> bool:
    """Open a tab on the given URL. False when no browser could be started."""
    try:
        return bool(webbrowser.open(url))
    except (webbrowser.Error, OSError):
        return False


def downloads_dir() -> Path:
    """The user's Downloads folder, whatever it is called in their language."""
    home = Path.home()
    if sys.platform.startswith("linux"):
        # A Japanese desktop has ~/ダウンロード; XDG records the real name here.
        config_home = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
        try:
            match = USER_DIRS_RE.search((config_home / "user-dirs.dirs").read_text(encoding="utf-8"))
        except OSError:
            match = None
        if match:
            candidate = Path(match.group("path").replace("$HOME", str(home)))
            if candidate.is_dir() and candidate != home:
                return candidate
    candidate = home / "Downloads"
    return candidate if candidate.is_dir() else home


def short_path(path: Path) -> str:
    """A path as people write it: ~/Downloads instead of /home/someone/Downloads."""
    try:
        return str(Path("~") / path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def open_path(path: Path) -> None:
    """Show a folder in the file manager, or a file selected inside its folder."""
    if not path.exists():
        raise AppError(f"Not found: {path}")
    try:
        if sys.platform == "win32":
            if path.is_dir():
                os.startfile(path)  # noqa: S606 - a folder we created ourselves
            else:
                subprocess.Popen(["explorer", f"/select,{path}"])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)] if path.is_dir() else ["open", "-R", str(path)])
        else:
            # There is no portable "select this file" on Linux, so open its folder.
            subprocess.Popen(
                ["xdg-open", str(path if path.is_dir() else path.parent)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except OSError as error:
        raise AppError(f"Could not open {path}: {error}") from error


def list_folders(raw: str) -> dict:
    """One level of the folder tree, for the 'choose a folder' dialog in the page."""
    path = Path(raw).expanduser() if raw else downloads_dir()
    try:
        path = path.resolve()
        if not path.is_dir():
            raise AppError(f"Not a folder: {path}")
        children = sorted(
            (child for child in path.iterdir() if child.is_dir() and not child.name.startswith(".")),
            key=lambda child: child.name.lower(),
        )
    except OSError as error:
        raise AppError(f"Could not read {raw or path}: {error}") from error

    home = Path.home()
    shortcuts = [home, downloads_dir(), home / "Desktop", home / "Music", home / "Videos", home / "Movies"]
    if sys.platform == "win32":
        # Python 3.12+; without it the drive letter can still be typed into the box.
        shortcuts += [Path(drive) for drive in getattr(os, "listdrives", list)()]
    return {
        "path": str(path),
        "parent": str(path.parent) if path.parent != path else "",
        "folders": [{"name": child.name, "path": str(child)} for child in children],
        "shortcuts": [
            {"name": place.name or str(place), "path": str(place)}
            for place in dict.fromkeys(shortcuts)
            if place.is_dir()
        ],
    }
