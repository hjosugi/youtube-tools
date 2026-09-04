import pytest

from ytcli.models import AppError
from ytcli.modes import ALL_MODES, MODE_LETTERS, MODE_NAMES, describe_modes, parse_modes


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("avs", "avs"),
        ("sva", "avs"),
        ("a", "a"),
        ("vs", "vs"),
        ("all", "avs"),
        ("audio,video", "av"),
        ("subs", "s"),
        ("sub", "s"),
        ("subtitles", "s"),
        ("mp3,mp4", "av"),
        ("a+v", "av"),
        ("AVS", "avs"),
        ("aa", "a"),
        ("  a , s ", "as"),
    ],
)
def test_parse_modes_normalises(raw, expected):
    assert parse_modes(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "x", "audio,x", "zz", ","])
def test_parse_modes_rejects_junk(raw):
    with pytest.raises(AppError):
        parse_modes(raw)


@pytest.mark.parametrize("raw", ["avs", "a", "vs", "all", "audio,video"])
def test_parse_modes_is_idempotent(raw):
    once = parse_modes(raw)
    assert parse_modes(once) == once


def test_constants_stay_in_step():
    assert MODE_LETTERS == tuple(MODE_NAMES)
    assert ALL_MODES == "".join(MODE_LETTERS)
    assert parse_modes("all") == ALL_MODES


def test_describe_modes():
    assert describe_modes("avs") == "audio, video, subtitle"
    assert describe_modes("") == "nothing"
