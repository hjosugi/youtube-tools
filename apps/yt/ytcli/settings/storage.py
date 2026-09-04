from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from typing import Any

from ..models import AppError

APP_NAME = "yt"
CONFIG_FILE_ENV = "YT_CONFIG_FILE"
CONFIG_FILENAME = "config.toml"


def config_path() -> Path:
    """Where the defaults live: $YT_CONFIG_FILE, else the platform config directory."""
    override = os.environ.get(CONFIG_FILE_ENV)
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_NAME / CONFIG_FILENAME


def load_config(defaults: dict[str, Any]) -> dict[str, Any]:
    """Read the config file over the given defaults. Unknown keys are ignored."""
    values = dict(defaults)
    path = config_path()
    if not path.is_file():
        return values
    try:
        stored = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise AppError(f"Could not read config {path}: {error}") from error

    for key, default in defaults.items():
        if key not in stored:
            continue
        value = stored[key]
        if isinstance(default, bool):
            if not isinstance(value, bool):
                raise AppError(f"Config key {key!r} in {path} must be true or false.")
            values[key] = value
        else:
            values[key] = str(value)
    return values


def save_config(values: dict[str, Any]) -> Path:
    """Write the given settings to the config file, replacing whatever was there."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# yt defaults. Delete a line to fall back to the built-in default.\n"
        "# Written by `yt --save-config`. Docs: https://github.com/hjosugi/youtube-tools\n\n"
    )
    path.write_text(header + format_config(values) + "\n", encoding="utf-8")
    return path


def format_config(values: dict[str, Any]) -> str:
    """Render settings as the TOML that save_config writes, aligned for reading."""
    width = max((len(key) for key in values), default=0)
    return "\n".join(f"{key.ljust(width)} = {_toml_value(value)}" for key, value in values.items())


def _toml_value(value: Any) -> str:
    """Quote and escape one value as a TOML literal."""
    if isinstance(value, bool):
        return "true" if value else "false"
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
