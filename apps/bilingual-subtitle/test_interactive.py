import argparse

from gen_subtitle.interactive import apply_interactive_options


def test_guided_setup_can_choose_english_only() -> None:
    answers = iter(
        [
            "https://youtube.com/watch?v=abc",
            "2",
            "lesson-out",
            "intro",
            "50",
            "",
        ]
    )
    args = argparse.Namespace(
        url="",
        translator="argos",
        deepl_auth_key="",
        out_dir="out",
        output_name="",
        en_only=False,
        batch_size=100,
    )

    result = apply_interactive_options(args, input_fn=lambda _prompt: next(answers), output_fn=lambda _line: None)

    assert result.url == "https://youtube.com/watch?v=abc"
    assert result.en_only is True
    assert result.out_dir == "lesson-out"
    assert result.output_name == "intro"
    assert result.batch_size == 50


if __name__ == "__main__":
    test_guided_setup_can_choose_english_only()
    print("ok")

