from pathlib import Path

import pytest

from ytcli.utils import (
    base_stem,
    clean_subtitle_text,
    language_of,
    normalize_timestamp,
    split_list,
    srt_timestamp,
    unique_path,
)


@pytest.mark.parametrize(
    ("name", "language", "expected"),
    [
        ("Some Title [dQw4w9WgXcQ].en.srt", "en", "Some Title"),
        ("Some Title [dQw4w9WgXcQ].mp4", "", "Some Title"),
        ("Talk 2.0 release [dQw4w9WgXcQ].ja.vtt", "ja", "Talk 2.0 release"),
        ("No id here.mp3", "", "No id here"),
        ("Title [dQw4w9WgXcQ].en-US.srt", "en-US", "Title"),
        ("Title [notanid].mp4", "", "Title [notanid]"),
    ],
)
def test_base_stem(name, language, expected):
    assert base_stem(Path(name), language) == expected


def test_base_stem_keeps_a_numeric_tail_that_is_not_an_extension():
    # 'Talk 2.0' has no real extension, so nothing should be stripped.
    assert base_stem(Path("Talk 2.0")) == "Talk 2.0"


def test_base_stem_truncates_long_titles():
    assert len(base_stem(Path("x" * 300 + " [dQw4w9WgXcQ].mp4"))) <= 120


def test_base_stem_never_returns_empty():
    assert base_stem(Path(".srt")) == "video"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("a [dQw4w9WgXcQ].en.srt", "en"),
        ("a [dQw4w9WgXcQ].en-US.vtt", "en-US"),
        ("a.mp4", ""),
        ("a.b.mp4", ""),
    ],
)
def test_language_of(name, expected):
    assert language_of(Path(name)) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("00:00:01,500", "00:00:01.500"),
        ("00:01.250", "00:00:01.250"),
        ("1:02:03.4", "01:02:03.400"),
        ("00:00:01", "00:00:01.000"),
    ],
)
def test_normalize_timestamp(raw, expected):
    assert normalize_timestamp(raw) == expected


@pytest.mark.parametrize("raw", ["00:00:01,500", "00:01.250", "1:02:03.4"])
def test_timestamp_helpers_are_idempotent(raw):
    once = normalize_timestamp(raw)
    assert normalize_timestamp(once) == once
    srt_once = srt_timestamp(raw)
    assert srt_timestamp(srt_once) == srt_once


def test_srt_timestamp_uses_comma():
    assert srt_timestamp("00:00:01.500") == "00:00:01,500"


def test_clean_subtitle_text_drops_tags_and_extra_space():
    assert clean_subtitle_text("<c>hello</c>\n  there <i>you</i>") == "hello there you"


def test_split_list_dedupes_and_trims():
    assert split_list(" en , ja ,en ") == ("en", "ja")
    assert split_list("en ja") == ("en", "ja")
    assert split_list("") == ()


@pytest.mark.parametrize("raw", ["en,ja", " en , ja ,en "])
def test_split_list_is_idempotent(raw):
    once = split_list(raw)
    assert split_list(",".join(once)) == once


def test_unique_path_returns_the_same_name_while_nothing_exists(tmp_path):
    target = tmp_path / "a.srt"
    assert unique_path(target) == unique_path(target) == target


def test_unique_path_avoids_overwrite(tmp_path):
    (tmp_path / "a.srt").write_text("x")
    assert unique_path(tmp_path / "a.srt").name == "a (2).srt"
    (tmp_path / "a (2).srt").write_text("x")
    assert unique_path(tmp_path / "a.srt").name == "a (3).srt"
