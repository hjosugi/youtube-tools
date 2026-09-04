import pytest

from ytcli.settings import Options
from ytcli.ui.wizard import PromptCancelled, run_wizard


def wizard(answers, options=None):
    stream = iter(answers)
    return run_wizard(
        options or Options(), input_fn=lambda _prompt: next(stream), output_fn=lambda _line: None
    )


def test_fills_every_option():
    options = wizard(
        [
            "https://youtu.be/abc https://youtu.be/def",  # urls
            "avs",  # modes
            "en,ja",  # subtitle languages
            "srt,md",  # subtitle formats
            "1080",  # video quality
            "mkv",  # video container
            "192",  # audio quality
            "opus",  # audio format
            "downloads",  # output
            "",  # confirm
        ]
    )
    assert options.urls == ["https://youtu.be/abc", "https://youtu.be/def"]
    assert options.modes == "avs"
    assert options.sub_langs == ("en", "ja")
    assert options.sub_formats == ("srt", "md")
    assert options.video_quality == "1080"
    assert options.video_format == "mkv"
    assert options.audio_quality == "192"
    assert options.audio_format == "opus"
    assert options.output == "downloads"


def test_keeps_defaults_on_empty_input():
    options = wizard(["https://youtu.be/abc", "", "", "", "", ""])
    assert options.modes == "s"
    assert options.sub_langs == ("en",)
    assert options.sub_formats == ("srt", "tsv")
    assert options.output == "."


def test_skips_the_questions_for_modes_that_were_not_chosen():
    # audio only: no subtitle and no video questions, so six answers are enough
    options = wizard(["URL", "a", "128", "mp3", "out", ""])
    assert options.modes == "a"
    assert options.audio_quality == "128"
    assert options.output == "out"


def test_retries_on_a_bad_mode():
    assert wizard(["URL", "zzz", "av", "", "", "", "", "", ""]).modes == "av"


def test_urls_can_be_comma_separated():
    options = wizard(["https://youtu.be/abc,https://youtu.be/def", "s", "", "", "", ""])
    assert options.urls == ["https://youtu.be/abc", "https://youtu.be/def"]


def test_urls_can_mix_commas_and_spaces_and_lose_repeats():
    options = wizard(["a, b  c ,a", "s", "", "", "", ""])
    assert options.urls == ["a", "b", "c"]


def test_keeps_urls_that_were_already_given():
    options = wizard(["s", "", "", "", ""], Options(urls=["already"]))
    assert options.urls == ["already"]


def test_can_be_cancelled():
    with pytest.raises(PromptCancelled):
        wizard(["URL", "s", "", "", "", "n"])
