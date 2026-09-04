from pathlib import Path

from ytcli.options import Options


def test_to_request_carries_every_setting(tmp_path):
    options = Options(
        urls=["URL"],
        modes="avs",
        output=str(tmp_path),
        sub_langs=("en", "ja"),
        sub_formats=("srt",),
        auto_subs=False,
        video_quality="720",
        video_format="mkv",
        audio_quality="192",
        audio_format="opus",
    )
    request = options.to_request("URL")

    assert request.out_dir == Path(tmp_path).resolve()
    assert request.wants_audio and request.wants_video and request.wants_subtitles
    assert request.sub_langs == ("en", "ja")
    assert request.auto_subs is False
    assert request.video_format == "mkv"
    assert request.audio_quality == "192"


def test_config_round_trip():
    options = Options(modes="av", sub_langs=("en", "ja"), sub_formats=("srt", "md"))
    restored = Options.from_config(options.to_config())
    assert restored.modes == "av"
    assert restored.sub_langs == ("en", "ja")
    assert restored.sub_formats == ("srt", "md")


def test_output_expands_user(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert Options(output="~/dl").out_dir == tmp_path / "dl"
