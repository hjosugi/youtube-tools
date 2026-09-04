import pytest

from ytcli.models import AppError
from ytcli.settings import storage

DEFAULTS = {"output": ".", "mode": "s", "auto_subs": True}


def test_missing_file_returns_the_given_defaults():
    assert storage.load_config(DEFAULTS) == DEFAULTS


def test_save_then_load_round_trip(isolated_config):
    values = DEFAULTS | {"output": "~/Downloads", "mode": "avs", "auto_subs": False}
    assert storage.save_config(values) == isolated_config
    assert storage.load_config(DEFAULTS) == values


def test_saving_creates_the_parent_directory(isolated_config):
    assert not isolated_config.parent.exists()
    storage.save_config(DEFAULTS)
    assert isolated_config.is_file()


def test_saving_twice_is_idempotent(isolated_config):
    storage.save_config(DEFAULTS)
    first = isolated_config.read_text()
    storage.save_config(DEFAULTS)
    assert isolated_config.read_text() == first


def test_windows_style_path_survives_escaping():
    storage.save_config(DEFAULTS | {"output": r"C:\Users\me\Videos"})
    assert storage.load_config(DEFAULTS)["output"] == r"C:\Users\me\Videos"


def test_quotes_in_a_value_survive():
    storage.save_config(DEFAULTS | {"output": 'dir "with" quotes'})
    assert storage.load_config(DEFAULTS)["output"] == 'dir "with" quotes'


def test_unknown_keys_are_ignored(isolated_config):
    isolated_config.parent.mkdir(parents=True)
    isolated_config.write_text('mode = "av"\nnonsense = 1\n', encoding="utf-8")
    loaded = storage.load_config(DEFAULTS)
    assert loaded["mode"] == "av"
    assert "nonsense" not in loaded


def test_broken_toml_raises_app_error(isolated_config):
    isolated_config.parent.mkdir(parents=True)
    isolated_config.write_text("mode = ", encoding="utf-8")
    with pytest.raises(AppError):
        storage.load_config(DEFAULTS)


def test_wrong_type_for_bool_raises(isolated_config):
    isolated_config.parent.mkdir(parents=True)
    isolated_config.write_text('auto_subs = "yes"\n', encoding="utf-8")
    with pytest.raises(AppError):
        storage.load_config(DEFAULTS)


def test_format_config_uses_toml_literals():
    rendered = storage.format_config({"mode": "avs", "auto_subs": False})
    assert 'mode      = "avs"' in rendered
    assert "auto_subs = false" in rendered
    assert "True" not in rendered and "False" not in rendered


@pytest.mark.parametrize(
    ("platform", "env", "expected_parts"),
    [
        ("linux", {"XDG_CONFIG_HOME": "/xdg"}, ("/xdg", "yt", "config.toml")),
        ("darwin", {}, ("Library", "Application Support", "yt", "config.toml")),
        ("win32", {"APPDATA": "/appdata"}, ("/appdata", "yt", "config.toml")),
    ],
)
def test_config_path_per_platform(monkeypatch, platform, env, expected_parts):
    monkeypatch.delenv(storage.CONFIG_FILE_ENV, raising=False)
    monkeypatch.setattr(storage.sys, "platform", platform)
    for key in ("XDG_CONFIG_HOME", "APPDATA"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    path = storage.config_path()
    for part in expected_parts:
        assert part in str(path)


def test_env_override_wins_over_the_platform_path(monkeypatch, tmp_path):
    monkeypatch.setenv(storage.CONFIG_FILE_ENV, str(tmp_path / "elsewhere.toml"))
    assert storage.config_path() == tmp_path / "elsewhere.toml"
