import pytest

from ytcli.models import AppError
from ytcli.modes import parse_modes
from ytcli.ui import prompts


def answering(*answers):
    """An input function that replies with the given answers in order."""
    stream = iter(answers)
    return lambda _prompt: next(stream)


def test_required_keeps_asking_until_something_is_typed():
    assert prompts.required("URL", answering("", "  ", "value")) == "value"


def test_text_keeps_the_default_on_an_empty_answer():
    assert prompts.text("Dir", ".", answering("")) == "."
    assert prompts.text("Dir", ".", answering("downloads")) == "downloads"


def test_parsed_retries_until_the_parser_accepts():
    output: list[str] = []
    assert prompts.parsed("Modes", "s", parse_modes, answering("zz", "av"), output.append) == "av"
    assert output and "Unknown mode" in output[0]


def test_parsed_falls_back_to_the_default():
    assert prompts.parsed("Modes", "avs", parse_modes, answering(""), print) == "avs"


def test_word_list_splits_and_keeps_the_default():
    assert prompts.word_list("Langs", ("en",), answering("en, ja")) == ("en", "ja")
    assert prompts.word_list("Langs", ("en",), answering("")) == ("en",)


def test_subset_rejects_unknown_values():
    output: list[str] = []
    chosen = prompts.subset("Formats", ("srt",), ("srt", "tsv"), answering("docx", "srt,tsv"), output.append)
    assert chosen == ("srt", "tsv")
    assert "Unknown value(s): docx" in output


def test_choice_rejects_anything_outside_the_list():
    output: list[str] = []
    assert prompts.choice("Q", ("best", "720"), "best", answering("4k", "720"), output.append) == "720"
    assert output


@pytest.mark.parametrize(
    ("answer", "default", "expected"),
    [("", True, True), ("", False, False), ("y", False, True), ("no", True, False)],
)
def test_yes_no(answer, default, expected):
    assert prompts.yes_no("Go", default, answering(answer), print) is expected


def test_yes_no_reasks_on_nonsense():
    output: list[str] = []
    assert prompts.yes_no("Go", True, answering("maybe", "n"), output.append) is False
    assert output == ["Please answer y or n."]


def test_prompt_cancelled_is_not_an_app_error():
    assert not issubclass(prompts.PromptCancelled, AppError)
