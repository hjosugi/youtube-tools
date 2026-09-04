import pytest

from ytcli.download import build_audio_quality, build_video_format
from ytcli.models import AUDIO_QUALITIES, VIDEO_FORMATS, VIDEO_QUALITIES


@pytest.mark.parametrize("quality", VIDEO_QUALITIES)
@pytest.mark.parametrize("container", VIDEO_FORMATS)
def test_every_combination_has_a_fallback(quality, container):
    assert "/" in build_video_format(quality, container)


def test_video_format_limits_height():
    assert "[height<=1080]" in build_video_format("1080", "mp4")


def test_best_and_worst_do_not_pin_a_height():
    assert "height" not in build_video_format("best", "mp4")
    assert "height" not in build_video_format("worst", "mp4")


def test_mp4_prefers_mp4_streams():
    assert "[ext=mp4]" in build_video_format("best", "mp4")
    assert "[ext=m4a]" in build_video_format("best", "mp4")


def test_non_mp4_container_does_not_force_mp4_streams():
    assert "[ext=mp4]" not in build_video_format("best", "mkv")
    assert "[ext=mp4]" not in build_video_format("720", "webm")


@pytest.mark.parametrize("quality", VIDEO_QUALITIES)
def test_building_a_format_is_pure(quality):
    assert build_video_format(quality, "mp4") == build_video_format(quality, "mp4")


def test_best_audio_quality_maps_to_vbr_zero():
    assert build_audio_quality("best") == "0"


@pytest.mark.parametrize("quality", [q for q in AUDIO_QUALITIES if q != "best"])
def test_a_numeric_audio_quality_is_passed_through(quality):
    assert build_audio_quality(quality) == quality
