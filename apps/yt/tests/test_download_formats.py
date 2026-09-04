import pytest

from ytcli.download import build_audio_quality, build_video_format


@pytest.mark.parametrize("quality", ["best", "1080", "worst"])
def test_video_format_always_has_a_fallback(quality):
    assert "/" in build_video_format(quality, "mp4")


def test_video_format_limits_height():
    assert "[height<=1080]" in build_video_format("1080", "mp4")


def test_mp4_prefers_mp4_streams():
    assert "[ext=mp4]" in build_video_format("best", "mp4")


def test_non_mp4_container_does_not_force_mp4_streams():
    assert "[ext=mp4]" not in build_video_format("best", "mkv")


def test_best_audio_quality_maps_to_vbr_zero():
    assert build_audio_quality("best") == "0"
    assert build_audio_quality("192") == "192"


class TestResolveSubtitleLangs:
    def test_exact_codes_are_used_as_is(self):
        from ytcli.download import resolve_subtitle_langs

        codes, warnings = resolve_subtitle_langs(("en", "de"), ["de", "en"], ["de", "en"])
        assert codes == ["en", "de"]
        assert warnings == []

    def test_never_expands_into_machine_translated_tracks(self):
        from ytcli.download import resolve_subtitle_langs

        # yt-dlp offers en-de / en-fr as machine translations of the English track.
        codes, _ = resolve_subtitle_langs(("en",), ["en"], ["en", "en-de", "en-fr", "ja"])
        assert codes == ["en"]

    def test_falls_back_to_a_regional_variant(self):
        from ytcli.download import resolve_subtitle_langs

        codes, warnings = resolve_subtitle_langs(("en",), [], ["en-US", "en-GB"])
        assert codes == ["en-GB"]
        assert warnings == []

    def test_prefers_the_original_track_over_a_region(self):
        from ytcli.download import resolve_subtitle_langs

        codes, _ = resolve_subtitle_langs(("en",), [], ["en-US", "en-orig"])
        assert codes == ["en-orig"]

    def test_missing_language_warns_and_keeps_the_others(self):
        from ytcli.download import resolve_subtitle_langs

        codes, warnings = resolve_subtitle_langs(("en", "ja"), ["en"], ["en"])
        assert codes == ["en"]
        assert len(warnings) == 1 and "ja" in warnings[0]

    def test_all_uses_every_available_track(self):
        from ytcli.download import resolve_subtitle_langs

        codes, warnings = resolve_subtitle_langs(("all",), ["en"], ["en", "de"])
        assert codes == ["en", "de"]
        assert warnings == []

    def test_all_on_a_video_without_subtitles_warns(self):
        from ytcli.download import resolve_subtitle_langs

        codes, warnings = resolve_subtitle_langs(("all",), [], [])
        assert codes == []
        assert warnings == ["this video has no subtitles"]

    def test_auto_subs_disabled_ignores_automatic_tracks(self):
        from ytcli.download import resolve_subtitle_langs

        codes, warnings = resolve_subtitle_langs(("en", "ja"), ["en"], ["en", "ja"], auto_subs=False)
        assert codes == ["en"]
        assert len(warnings) == 1

    def test_case_insensitive_match(self):
        from ytcli.download import resolve_subtitle_langs

        codes, _ = resolve_subtitle_langs(("EN",), ["en"], [])
        assert codes == ["en"]

    def test_duplicate_requests_are_collapsed(self):
        from ytcli.download import resolve_subtitle_langs

        codes, _ = resolve_subtitle_langs(("en", "en-US"), ["en", "en-US"], [])
        assert codes == ["en", "en-US"]
