import pytest

from ytcli.models import SubtitleCue
from ytcli.subtitles import SUBTITLE_FORMATS, SUBTITLE_WRITERS

CUES = [
    SubtitleCue("00:00:01.000", "00:00:02.000", "Hello"),
    SubtitleCue("00:00:02.000", "00:00:03.000", "World"),
]


def test_the_format_list_is_derived_from_the_writers():
    assert SUBTITLE_FORMATS == tuple(SUBTITLE_WRITERS)


@pytest.mark.parametrize("fmt", SUBTITLE_FORMATS)
def test_every_writer_produces_a_non_empty_file(tmp_path, fmt):
    path = tmp_path / f"a.{fmt}"
    SUBTITLE_WRITERS[fmt](CUES, path)
    text = path.read_text(encoding="utf-8")
    assert "Hello" in text and "World" in text


@pytest.mark.parametrize("fmt", SUBTITLE_FORMATS)
def test_writing_twice_gives_the_same_file(tmp_path, fmt):
    first, second = tmp_path / "one" / f"a.{fmt}", tmp_path / "two" / f"a.{fmt}"
    for path in (first, second):
        path.parent.mkdir()
        SUBTITLE_WRITERS[fmt](CUES, path)
    assert first.read_bytes() == second.read_bytes()


def test_srt_uses_comma_milliseconds(tmp_path):
    path = tmp_path / "a.srt"
    SUBTITLE_WRITERS["srt"](CUES, path)
    text = path.read_text(encoding="utf-8")
    assert text.startswith("1\n")
    assert "00:00:01,000 --> 00:00:02,000" in text


def test_vtt_has_header(tmp_path):
    path = tmp_path / "a.vtt"
    SUBTITLE_WRITERS["vtt"](CUES, path)
    assert path.read_text(encoding="utf-8").startswith("WEBVTT")


def test_tsv_has_header_and_rows(tmp_path):
    path = tmp_path / "a.tsv"
    SUBTITLE_WRITERS["tsv"](CUES, path)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0].split("\t") == ["no", "start", "end", "text"]
    assert lines[1].split("\t") == ["1", "00:00:01.000", "00:00:02.000", "Hello"]


def test_txt_is_text_only(tmp_path):
    path = tmp_path / "a.txt"
    SUBTITLE_WRITERS["txt"](CUES, path)
    assert path.read_text(encoding="utf-8") == "Hello\nWorld\n"


def test_md_has_numbered_sections(tmp_path):
    path = tmp_path / "a.md"
    SUBTITLE_WRITERS["md"](CUES, path)
    text = path.read_text(encoding="utf-8")
    assert "## 1" in text and "## 2" in text
