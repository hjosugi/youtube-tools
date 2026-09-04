import pytest

from ytcli import config as config_module
from ytcli.cli import apply_overrides, build_parser
from ytcli.models import AppError
from ytcli.options import Options


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv(config_module.CONFIG_FILE_ENV, str(tmp_path / "config.toml"))


def resolve(argv, config=None):
    args = build_parser().parse_args(argv)
    return apply_overrides(Options.from_config(config or config_module.DEFAULTS), args)


def test_defaults_are_english_subtitles_only():
    options = resolve(["https://youtu.be/abc"])
    assert options.modes == "s"
    assert options.sub_langs == ("en",)
    assert options.sub_formats == ("srt", "tsv")


def test_mode_letters():
    assert resolve(["URL", "-m", "avs"]).modes == "avs"
    assert resolve(["URL", "-m", "a"]).modes == "a"


def test_language_list():
    assert resolve(["URL", "-m", "s", "-l", "en,ja"]).sub_langs == ("en", "ja")
    assert resolve(["URL", "-m", "s", "-l", "all"]).sub_langs == ("all",)


def test_subtitle_format_selection():
    assert resolve(["URL", "-f", "srt,md"]).sub_formats == ("srt", "md")


def test_unknown_subtitle_format_is_rejected():
    with pytest.raises(AppError):
        resolve(["URL", "-f", "docx"])


def test_quality_flags():
    options = resolve(["URL", "-m", "av", "--vq", "1080", "--aq", "192"])
    assert options.video_quality == "1080"
    assert options.audio_quality == "192"


def test_long_quality_aliases_match_short_ones():
    assert resolve(["URL", "--video-quality", "720"]).video_quality == "720"
    assert resolve(["URL", "--audio-quality", "128"]).audio_quality == "128"


def test_config_supplies_defaults_and_cli_wins():
    config = dict(config_module.DEFAULTS) | {"output": "/data", "mode": "av", "sub_langs": "ja"}
    assert resolve(["URL"], config).output == "/data"
    assert resolve(["URL"], config).modes == "av"
    assert resolve(["URL", "-o", "/other"], config).output == "/other"
    assert resolve(["URL", "-m", "s"], config).modes == "s"


def test_no_auto_subs_flag():
    assert resolve(["URL"]).auto_subs is True
    assert resolve(["URL", "--no-auto-subs"]).auto_subs is False


def test_config_path_command_prints_path(capsys):
    from ytcli.cli import main

    assert main(["--config-path"]) == 0
    assert "config.toml" in capsys.readouterr().out


def test_show_config_command(capsys):
    from ytcli.cli import main

    assert main(["--show-config"]) == 0
    out = capsys.readouterr().out
    assert "sub_formats" in out and "mode" in out


def test_save_config_without_url_exits_cleanly(capsys):
    from ytcli.cli import main

    assert main(["--save-config", "-o", "/tmp/dl", "-m", "av"]) == 0
    assert config_module.load_config()["output"] == "/tmp/dl"
    assert config_module.load_config()["mode"] == "av"
    assert "Saved defaults" in capsys.readouterr().out


def test_bad_mode_reports_error_without_traceback(capsys):
    from ytcli.cli import main

    assert main(["URL", "-m", "x"]) == 1
    assert "error:" in capsys.readouterr().err
