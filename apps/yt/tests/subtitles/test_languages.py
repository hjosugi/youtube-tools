import pytest

from ytcli.models import SubtitleTracks
from ytcli.subtitles import resolve_subtitle_langs


def tracks(manual=(), automatic=()):
    return SubtitleTracks(manual=tuple(manual), automatic=tuple(automatic))


def test_exact_codes_are_used_as_is():
    codes, warnings = resolve_subtitle_langs(("en", "de"), tracks(["de", "en"], ["de", "en"]))
    assert codes == ["en", "de"]
    assert warnings == []


def test_never_expands_into_machine_translated_tracks():
    # yt-dlp offers en-de / en-fr as machine translations of the English track.
    codes, _ = resolve_subtitle_langs(("en",), tracks(["en"], ["en", "en-de", "en-fr", "ja"]))
    assert codes == ["en"]


def test_falls_back_to_a_regional_variant():
    codes, warnings = resolve_subtitle_langs(("en",), tracks([], ["en-US", "en-GB"]))
    assert codes == ["en-GB"]
    assert warnings == []


def test_prefers_the_original_track_over_a_region():
    codes, _ = resolve_subtitle_langs(("en",), tracks([], ["en-US", "en-orig"]))
    assert codes == ["en-orig"]


def test_missing_language_warns_and_keeps_the_others():
    codes, warnings = resolve_subtitle_langs(("en", "ja"), tracks(["en"], ["en"]))
    assert codes == ["en"]
    assert len(warnings) == 1 and "ja" in warnings[0]


def test_all_uses_every_available_track():
    codes, warnings = resolve_subtitle_langs(("all",), tracks(["en"], ["en", "de"]))
    assert codes == ["en", "de"]
    assert warnings == []


def test_all_on_a_video_without_subtitles_warns():
    codes, warnings = resolve_subtitle_langs(("all",), tracks())
    assert codes == []
    assert warnings == ["this video has no subtitles"]


def test_auto_subs_disabled_ignores_automatic_tracks():
    codes, warnings = resolve_subtitle_langs(("en", "ja"), tracks(["en"], ["en", "ja"]), False)
    assert codes == ["en"]
    assert len(warnings) == 1


def test_case_insensitive_match():
    codes, _ = resolve_subtitle_langs(("EN",), tracks(["en"]))
    assert codes == ["en"]


def test_duplicate_requests_are_collapsed():
    codes, _ = resolve_subtitle_langs(("en", "en", "en-US"), tracks(["en", "en-US"]))
    assert codes == ["en", "en-US"]


@pytest.mark.parametrize("requested", [("en",), ("all",), ("en", "ja")])
def test_resolution_is_pure_and_repeatable(requested):
    available = tracks(["en"], ["en", "de"])
    assert resolve_subtitle_langs(requested, available) == resolve_subtitle_langs(requested, available)
