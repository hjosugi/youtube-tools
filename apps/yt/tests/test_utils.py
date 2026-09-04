from pathlib import Path

import pytest

from ytcli.utils import base_stem, language_of, normalize_timestamp, split_list, srt_timestamp, unique_path


@pytest.mark.parametrize(
    ("name", "language", "expected"),
    [
        ("Some Title [dQw4w9WgXcQ].en.srt", "en", "Some Title"),
        ("Some Title [dQw4w9WgXcQ].mp4", "", "Some Title"),
        ("Talk 2.0 release [dQw4w9WgXcQ].ja.vtt", "ja", "Talk 2.0 release"),
        ("No id here.mp3", "", "No id here"),
        ("Title [dQw4w9WgXcQ].en-US.srt", "en-US", "Title"),
    ],
)
def test_base_stem(name, language, expected):
    assert base_stem(Path(name), language) == expected


def test_base_stem_truncates_long_titles():
    long_name = "x" * 300 + " [dQw4w9WgXcQ].mp4"
    assert len(base_stem(Path(long_name))) <= 120


@pytest.mark.parametrize(
    ("name", "expected"),
    [("a [dQw4w9WgXcQ].en.srt", "en"), ("a [dQw4w9WgXcQ].en-US.vtt", "en-US"), ("a.mp4", "")],
)
def test_language_of(name, expected):
    assert language_of(Path(name)) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("00:00:01,500", "00:00:01.500"),
        ("00:01.250", "00:00:01.250"),
        ("1:02:03.4", "01:02:03.400"),
    ],
)
def test_normalize_timestamp(raw, expected):
    assert normalize_timestamp(raw) == expected


def test_srt_timestamp_uses_comma():
    assert srt_timestamp("00:00:01.500") == "00:00:01,500"


def test_split_list_dedupes_and_trims():
    assert split_list(" en , ja ,en ") == ("en", "ja")
    assert split_list("") == ()


def test_unique_path_avoids_overwrite(tmp_path):
    target = tmp_path / "a.srt"
    target.write_text("x")
    assert unique_path(target).name == "a (2).srt"
