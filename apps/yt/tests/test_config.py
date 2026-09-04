import pytest

from ytcli import config as config_module
from ytcli.models import AppError


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    path = tmp_path / "config.toml"
    monkeypatch.setenv(config_module.CONFIG_FILE_ENV, str(path))
    return path


def test_missing_file_returns_defaults(config_file):
    assert config_module.load_config() == config_module.DEFAULTS


def test_save_then_load_round_trip(config_file):
    values = dict(config_module.DEFAULTS)
    values.update({"output": "~/Downloads", "mode": "avs", "auto_subs": False})
    saved_path = config_module.save_config(values)

    assert saved_path == config_file
    loaded = config_module.load_config()
    assert loaded["output"] == "~/Downloads"
    assert loaded["mode"] == "avs"
    assert loaded["auto_subs"] is False


def test_windows_style_path_survives_escaping(config_file):
    values = dict(config_module.DEFAULTS) | {"output": r"C:\Users\me\Videos"}
    config_module.save_config(values)
    assert config_module.load_config()["output"] == r"C:\Users\me\Videos"


def test_unknown_keys_are_ignored(config_file):
    config_file.write_text('mode = "av"\nnonsense = 1\n', encoding="utf-8")
    loaded = config_module.load_config()
    assert loaded["mode"] == "av"
    assert "nonsense" not in loaded


def test_broken_toml_raises_app_error(config_file):
    config_file.write_text("mode = ", encoding="utf-8")
    with pytest.raises(AppError):
        config_module.load_config()


def test_wrong_type_for_bool_raises(config_file):
    config_file.write_text('auto_subs = "yes"\n', encoding="utf-8")
    with pytest.raises(AppError):
        config_module.load_config()


def test_format_config_matches_file_syntax(config_file):
    values = dict(config_module.DEFAULTS) | {"auto_subs": False, "mode": "avs"}
    rendered = config_module.format_config(values)
    assert "auto_subs" in rendered and "false" in rendered
    assert 'mode          = "avs"' in rendered
    assert "True" not in rendered and "False" not in rendered
