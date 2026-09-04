"""Keep every test away from the developer's real config file."""

import pytest

from ytcli.settings import storage


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Point $YT_CONFIG_FILE at a throwaway file for the whole test session."""
    path = tmp_path / "config" / "config.toml"
    monkeypatch.setenv(storage.CONFIG_FILE_ENV, str(path))
    return path
