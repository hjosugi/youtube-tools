import pytest

from ytcli.interactive import PromptCancelled, run_wizard
from ytcli.options import Options


def wizard(answers):
    stream = iter(answers)
    return run_wizard(Options(), input_fn=lambda _prompt: next(stream), output_fn=lambda _line: None)


def test_wizard_fills_every_option():
    options = wizard(
        [
            "https://youtu.be/abc https://youtu.be/def",  # urls
            "avs",  # modes
            "en,ja",  # subtitle languages
            "srt,md",  # subtitle formats
            "1080",  # video quality
            "mp4",  # video container
            "192",  # audio quality
            "mp3",  # audio format
            "downloads",  # output
            "",  # confirm
        ]
    )
    assert options.urls == ["https://youtu.be/abc", "https://youtu.be/def"]
    assert options.modes == "avs"
    assert options.sub_langs == ("en", "ja")
    assert options.sub_formats == ("srt", "md")
    assert options.video_quality == "1080"
    assert options.audio_quality == "192"
    assert options.output == "downloads"


def test_wizard_keeps_defaults_on_empty_input():
    options = wizard(["https://youtu.be/abc", "", "", "", "", ""])
    assert options.modes == "s"
    assert options.sub_langs == ("en",)
    assert options.sub_formats == ("srt", "tsv")
    assert options.output == "."


def test_wizard_retries_on_bad_mode():
    options = wizard(["URL", "zzz", "av", "", "", "", "", "", ""])
    assert options.modes == "av"


def test_wizard_can_be_cancelled():
    with pytest.raises(PromptCancelled):
        wizard(["URL", "s", "", "", "", "n"])
