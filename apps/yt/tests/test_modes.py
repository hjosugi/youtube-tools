import pytest

from ytcli.models import AppError
from ytcli.modes import describe_modes, parse_modes


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
        ("a+v", "av"),
        ("AVS", "avs"),
        ("aa", "a"),
    ],
)
def test_parse_modes_normalises(raw, expected):
    assert parse_modes(raw) == expected


@pytest.mark.parametrize("raw", ["", "x", "audio,x", "zz"])
def test_parse_modes_rejects_junk(raw):
    with pytest.raises(AppError):
        parse_modes(raw)


def test_describe_modes():
    assert describe_modes("avs") == "audio, video, subtitle"
