import pytest

from ytcli.models import AppError
from ytcli.settings import DEFAULTS, Options
from ytcli.ui.args import apply_overrides, build_parser, epilog


def resolve(argv, config=None) -> Options:
    args = build_parser().parse_args(argv)
    return apply_overrides(Options.from_config(config or DEFAULTS), args)


def test_without_flags_the_defaults_survive():
    options = resolve(["https://youtu.be/abc"])
    assert options.urls == ["https://youtu.be/abc"]
    assert options.modes == "s"
    assert options.sub_langs == ("en",)
    assert options.sub_formats == ("srt", "tsv")


@pytest.mark.parametrize(
    ("flag", "expected"), [("avs", "avs"), ("a", "a"), ("all", "avs"), ("audio,video", "av")]
)
def test_mode_flag(flag, expected):
    assert resolve(["URL", "-m", flag]).modes == expected


def test_language_list():
    assert resolve(["URL", "-l", "en,ja"]).sub_langs == ("en", "ja")
    assert resolve(["URL", "--lang", "all"]).sub_langs == ("all",)


def test_subtitle_format_selection():
    assert resolve(["URL", "-f", "srt,md"]).sub_formats == ("srt", "md")
    assert resolve(["URL", "--sub-format", "tsv"]).sub_formats == ("tsv",)


def test_unknown_subtitle_format_is_rejected():
    with pytest.raises(AppError):
        resolve(["URL", "-f", "docx"])


def test_quality_flags():
    options = resolve(["URL", "-m", "av", "--vq", "1080", "--aq", "192"])
    assert options.video_quality == "1080"
    assert options.audio_quality == "192"


def test_long_quality_aliases_match_the_short_ones():
    assert resolve(["URL", "--video-quality", "720"]).video_quality == "720"
    assert resolve(["URL", "--audio-quality", "128"]).audio_quality == "128"


def test_container_and_codec_flags():
    options = resolve(["URL", "--video-format", "mkv", "--audio-format", "flac"])
    assert options.video_format == "mkv"
    assert options.audio_format == "flac"


@pytest.mark.parametrize("argv", [["URL", "--vq", "4320"], ["URL", "--audio-format", "aac"]])
def test_argparse_rejects_values_outside_the_choice_list(argv):
    with pytest.raises(SystemExit):
        build_parser().parse_args(argv)


def test_config_supplies_defaults_and_the_cli_wins():
    config = DEFAULTS | {"output": "/data", "mode": "av", "sub_langs": "ja"}
    assert resolve(["URL"], config).output == "/data"
    assert resolve(["URL"], config).modes == "av"
    assert resolve(["URL"], config).sub_langs == ("ja",)
    assert resolve(["URL", "-o", "/other"], config).output == "/other"
    assert resolve(["URL", "-m", "s"], config).modes == "s"


def test_no_auto_subs_flag():
    assert resolve(["URL"]).auto_subs is True
    assert resolve(["URL", "--no-auto-subs"]).auto_subs is False


def test_insecure_is_off_unless_asked_for():
    assert resolve(["URL"]).insecure is False
    assert resolve(["URL", "--insecure"]).insecure is True


def test_several_urls_are_kept_in_order():
    assert resolve(["a", "b", "c"]).urls == ["a", "b", "c"]


def test_epilog_follows_the_config_path(isolated_config):
    assert str(isolated_config) in epilog()
