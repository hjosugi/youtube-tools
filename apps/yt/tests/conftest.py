"""Keep every test away from the developer's real config, cache, network and desktop."""

import pytest

from ytcli import ffmpeg
from ytcli.models import AppError
from ytcli.settings import storage
from ytcli.ui.web import system


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Point $YT_CONFIG_FILE at a throwaway file for the whole test session."""
    path = tmp_path / "config" / "config.toml"
    monkeypatch.setenv(storage.CONFIG_FILE_ENV, str(path))
    return path


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Keep the ffmpeg cache in a throwaway directory and never download the real thing."""

    def refuse(*_args, **_kwargs):
        raise AppError("tests must not download ffmpeg")

    monkeypatch.setenv(ffmpeg.CACHE_DIR_ENV, str(tmp_path / "cache"))
    monkeypatch.setattr(ffmpeg, "fetch", refuse)
    return tmp_path / "cache"


@pytest.fixture(autouse=True)
def desktop(monkeypatch):
    """Record instead of opening browser tabs and file managers on the machine running tests."""
    opened = {"browser": [], "paths": []}
    monkeypatch.setattr(system, "open_browser", lambda url: opened["browser"].append(url) or True)
    monkeypatch.setattr(system, "open_path", lambda path: opened["paths"].append(path))
    return opened
