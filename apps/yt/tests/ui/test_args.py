import sys

import pytest

from ytcli.models import AppError
from ytcli.settings import DEFAULTS, Options
from ytcli.ui.args import apply_overrides, build_parser, command_line, epilog, parse_args


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


class TestWords:
    def test_mode_words_are_not_urls(self):
        args = parse_args(["mp3", "https://youtu.be/a", "sub"])
        assert args.urls == ["https://youtu.be/a"]
        assert args.mode == "mp3,sub"

    def test_words_add_to_the_mode_flag(self):
        args = parse_args(["URL", "-m", "v", "MP3"])
        options = apply_overrides(Options.from_config(DEFAULTS), args)
        assert options.modes == "av"

    def test_ui_words_set_the_flag(self):
        assert parse_args(["ui"]).gui is True
        assert parse_args(["gui", "URL"]).urls == ["URL"]

    def test_without_words_nothing_changes(self):
        args = parse_args(["URL"])
        assert (args.urls, args.mode, args.gui) == (["URL"], None, False)

    def test_words_urls_and_flags_may_come_in_any_order(self):
        args = parse_args(["mp3", "--aq", "192", "URL1", "-o", "/tmp/dl", "URL2"])
        assert args.urls == ["URL1", "URL2"]
        assert (args.mode, args.audio_quality, args.output) == ("mp3", "192", "/tmp/dl")


class TestCommandLine:
    """The line shown under a job: the same download as a command."""

    def test_words_for_the_usual_formats(self):
        assert command_line(Options(modes="a", output="/dl"), "URL") == "yt mp3 URL -o /dl"
        assert command_line(Options(modes="v", output="/dl"), "URL") == "yt mp4 URL -o /dl"
        assert command_line(Options(modes="s", output="/dl"), "URL") == "yt sub URL -o /dl"
        assert command_line(Options(modes="avs", output="/dl"), "URL") == "yt all URL -o /dl"
        assert command_line(Options(modes="as", output="/dl"), "URL") == "yt mp3 sub URL -o /dl"

    def test_other_formats_use_the_plain_words(self):
        line = command_line(Options(modes="av", output="/dl", audio_format="flac", video_format="mkv"), "URL")
        assert line == "yt audio video URL --video-format mkv --audio-format flac -o /dl"

    def test_only_settings_that_differ_from_the_defaults_are_spelled_out(self):
        chosen = Options(
            modes="avs",
            output="/dl",
            sub_langs=("ja", "en"),
            sub_formats=("srt",),
            auto_subs=False,
            video_quality="1080",
            audio_quality="192",
        )
        assert command_line(chosen, "URL") == (
            "yt all URL -l ja,en -f srt --no-auto-subs --vq 1080 --aq 192 -o /dl"
        )

    def test_flags_of_modes_not_asked_for_are_left_out(self):
        chosen = Options(modes="s", output="/dl", video_quality="720", audio_quality="64")
        assert command_line(chosen, "URL") == "yt sub URL -o /dl"

    def test_the_url_is_quoted_for_the_shell(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        assert "'https://y/watch?v=a&t=1'" in command_line(Options(modes="a"), "https://y/watch?v=a&t=1")
        monkeypatch.setattr(sys, "platform", "win32")
        assert command_line(Options(modes="a", output="C:\\My Files"), "URL").endswith('-o "C:\\My Files"')
