import argparse

from yt_fetcher.interactive import apply_interactive_options


def test_guided_setup_selects_formats_and_output() -> None:
    answers = iter(
        [
            "https://youtube.com/watch?v=abc",
            "",
            "y",
            "y",
            "720",
            "downloads",
            "",
        ]
    )
    args = argparse.Namespace(
        urls=[],
        subtitles=False,
        mp3=False,
        mp4=False,
        resolution="best",
        output=".",
    )

    result = apply_interactive_options(args, input_fn=lambda _prompt: next(answers), output_fn=lambda _line: None)

    assert result.urls == ["https://youtube.com/watch?v=abc"]
    assert result.subtitles is True
    assert result.mp3 is True
    assert result.mp4 is True
    assert result.resolution == "720"
    assert result.output == "downloads"


if __name__ == "__main__":
    test_guided_setup_selects_formats_and_output()
    print("ok")

