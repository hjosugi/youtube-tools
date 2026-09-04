"""The desktop window. Tk is imported lazily so the CLI works without it."""

from __future__ import annotations

from ...models import AppError
from ...settings import Options

MISSING_TK = (
    "The GUI needs Tk, which is missing from this Python build.\n"
    "Install it (Debian/Ubuntu: `sudo apt install python3-tk`, "
    "Fedora: `sudo dnf install python3-tkinter`, Arch: `sudo pacman -S tk`) "
    "or use the terminal wizard with `yt -i`."
)


def run_gui(options: Options | None = None) -> int:
    """Open the window and block until it closes."""
    try:
        import tkinter as tk
    except ImportError as error:
        raise AppError(MISSING_TK) from error

    from .app import App

    root = tk.Tk()
    App(root, options or Options())
    root.mainloop()
    return 0
