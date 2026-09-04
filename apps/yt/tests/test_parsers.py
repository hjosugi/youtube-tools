import pytest

from ytcli.models import AppError
from ytcli.parsers import parse_subtitle_file

SRT = """1
00:00:01,000 --> 00:00:02,000
Hello <i>there</i>

2
00:00:02,000 --> 00:00:03,000
Hello there

3
00:00:03,000 --> 00:00:04,500
Second line
"""

VTT = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:02.000 align:start position:0%
Hello there

00:00:02.500 --> 00:00:03.000
<c>Second</c> line
"""


def test_parse_srt_collapses_repeated_lines(tmp_path):
    path = tmp_path / "a.srt"
    path.write_text(SRT, encoding="utf-8")
    cues = parse_subtitle_file(path)
    assert [cue.text for cue in cues] == ["Hello there", "Second line"]
    # the collapsed cue keeps the start of the first and the end of the last
    assert cues[0].start == "00:00:01.000"
    assert cues[0].end == "00:00:03.000"


def test_parse_vtt_strips_tags_and_cue_settings(tmp_path):
    path = tmp_path / "a.vtt"
    path.write_text(VTT, encoding="utf-8")
    cues = parse_subtitle_file(path)
    assert [cue.text for cue in cues] == ["Hello there", "Second line"]
    assert cues[1].start == "00:00:02.500"


def test_unknown_extension_raises(tmp_path):
    path = tmp_path / "a.ass"
    path.write_text("x", encoding="utf-8")
    with pytest.raises(AppError):
        parse_subtitle_file(path)


def test_empty_subtitle_raises(tmp_path):
    path = tmp_path / "a.srt"
    path.write_text("\n", encoding="utf-8")
    with pytest.raises(AppError):
        parse_subtitle_file(path)
