from pathlib import Path

import pytest

from ytcli.models import AppError
from ytcli.settings import DEFAULTS, Options, save_config


def test_defaults_dict_matches_a_bare_options():
    # DEFAULTS is derived from Options(), so the two can never drift apart.
    assert DEFAULTS == Options().to_config()
    assert Options.from_config() == Options()


def test_defaults_are_english_subtitles_as_srt_and_tsv():
    options = Options()
    assert options.modes == "s"
    assert options.sub_langs == ("en",)
    assert options.sub_formats == ("srt", "tsv")
    assert options.output == "."


def test_config_round_trip():
    options = Options(modes="av", sub_langs=("en", "ja"), sub_formats=("srt", "md"))
    restored = Options.from_config(options.to_config())
    assert restored.modes == "av"
    assert restored.sub_langs == ("en", "ja")
    assert restored.sub_formats == ("srt", "md")


def test_round_trip_is_idempotent():
    options = Options(modes="avs", video_quality="720", audio_format="opus")
    once = Options.from_config(options.to_config())
    assert Options.from_config(once.to_config()) == once


def test_to_config_leaves_out_per_run_values():
    stored = Options(urls=["URL"], insecure=True).to_config()
    assert "urls" not in stored and "insecure" not in stored


def test_load_reads_the_saved_file():
    save_config(Options(modes="av", output="/data").to_config())
    loaded = Options.load()
    assert loaded.modes == "av"
    assert loaded.output == "/data"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("video_quality", "9999"),
        ("video_format", "avi"),
        ("audio_quality", "1000"),
        ("audio_format", "aac"),
        ("mode", "x"),
        ("sub_formats", "docx"),
    ],
)
def test_a_bad_config_value_is_rejected(key, value):
    with pytest.raises(AppError):
        Options.from_config(DEFAULTS | {key: value})


def test_empty_language_list_falls_back_to_english():
    assert Options.from_config(DEFAULTS | {"sub_langs": ""}).sub_langs == ("en",)


def test_empty_format_list_falls_back_to_srt():
    assert Options.from_config(DEFAULTS | {"sub_formats": ""}).sub_formats == ("srt",)


def test_out_dir_expands_user(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert Options(output="~/dl").out_dir == tmp_path / "dl"


def test_out_dir_is_absolute():
    assert Options(output=".").out_dir == Path.cwd()
