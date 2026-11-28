from pathlib import Path

import pytest

from ytcli.download import download, stages
from ytcli.download.client import silent
from ytcli.download.job import Job
from ytcli.models import AppError, DownloadCancelled, DownloadResult, SubtitleTracks
from ytcli.settings import Options

# Taken before the `fake` fixture swaps it for a stub.
real_prepare_ffmpeg = stages.prepare_ffmpeg

SRT = "1\n00:00:01,000 --> 00:00:02,000\nHello\n\n2\n00:00:02,000 --> 00:00:03,000\nWorld\n"

VIDEO_FILE = ("Clip [dQw4w9WgXcQ].mp4", "video-bytes")
AUDIO_FILE = ("Clip [dQw4w9WgXcQ].mp3", "audio-bytes")
SUB_FILE = ("Clip [dQw4w9WgXcQ].en.srt", SRT)


def options(tmp_path, **overrides) -> Options:
    return Options(output=str(tmp_path), **overrides)


def test_downloads_all_three_modes(tmp_path, fake):
    fake.produce = {"subs": [SUB_FILE], "audio": [AUDIO_FILE], "video": [VIDEO_FILE]}
    result = download(options(tmp_path, modes="avs"), "URL", log=lambda _line: None)

    assert sorted(path.name for path in result.files) == [
        "Clip.en.srt",
        "Clip.en.tsv",
        "Clip.mp3",
        "Clip.mp4",
    ]
    assert result.warnings == []


def test_runs_subtitles_before_the_media(tmp_path, fake):
    fake.produce = {"subs": [SUB_FILE], "audio": [AUDIO_FILE], "video": [VIDEO_FILE]}
    download(options(tmp_path, modes="avs"), "URL", log=lambda _line: None)
    assert fake.stages_run == ["subs", "audio", "video"]


@pytest.mark.parametrize(
    ("modes", "expected"),
    [("s", ["subs"]), ("a", ["audio"]), ("v", ["video"]), ("av", ["audio", "video"])],
)
def test_only_the_requested_stages_run(tmp_path, fake, modes, expected):
    fake.produce = {"subs": [SUB_FILE], "audio": [AUDIO_FILE], "video": [VIDEO_FILE]}
    download(options(tmp_path, modes=modes), "URL", log=lambda _line: None)
    assert fake.stages_run == expected


def test_writes_every_requested_subtitle_format(tmp_path, fake):
    fake.produce = {"subs": [SUB_FILE]}
    result = download(
        options(tmp_path, modes="s", sub_formats=("srt", "vtt", "tsv", "txt", "md")),
        "URL",
        log=lambda _line: None,
    )
    assert sorted(path.suffix for path in result.files) == [".md", ".srt", ".tsv", ".txt", ".vtt"]


def test_one_file_per_language(tmp_path, fake):
    fake.tracks = SubtitleTracks(("de", "en"), ())
    fake.produce = {"subs": [SUB_FILE, ("Clip [dQw4w9WgXcQ].de.srt", SRT)]}
    result = download(
        options(tmp_path, modes="s", sub_langs=("en", "de"), sub_formats=("srt",)),
        "URL",
        log=lambda _line: None,
    )
    assert sorted(path.name for path in result.files) == ["Clip.de.srt", "Clip.en.srt"]


def test_asks_yt_dlp_only_for_codes_that_exist(tmp_path, fake):
    fake.tracks = SubtitleTracks(("en",), ("en", "en-de"))
    fake.produce = {"subs": [SUB_FILE]}
    download(options(tmp_path, modes="s"), "URL", log=lambda _line: None)
    assert fake.options_for("subs")["subtitleslangs"] == ["en"]


def test_auto_captions_are_not_requested_for_a_manual_track(tmp_path, fake):
    fake.tracks = SubtitleTracks(("en",), ("en",))
    fake.produce = {"subs": [SUB_FILE]}
    download(options(tmp_path, modes="s"), "URL", log=lambda _line: None)
    assert fake.options_for("subs")["writeautomaticsub"] is False


def test_auto_captions_are_requested_when_only_they_have_the_language(tmp_path, fake):
    fake.tracks = SubtitleTracks((), ("en",))
    fake.produce = {"subs": [SUB_FILE]}
    download(options(tmp_path, modes="s"), "URL", log=lambda _line: None)
    assert fake.options_for("subs")["writeautomaticsub"] is True


def test_media_keeps_its_extension_and_loses_the_video_id(tmp_path, fake):
    fake.produce = {"video": [VIDEO_FILE]}
    result = download(options(tmp_path, modes="v"), "URL", log=lambda _line: None)
    assert result.files[0].name == "Clip.mp4"
    assert result.files[0].read_text() == "video-bytes"


def test_a_failing_stage_warns_but_lets_the_others_finish(tmp_path, fake):
    fake.fail = {"audio"}
    fake.produce = {"video": [VIDEO_FILE]}
    result = download(options(tmp_path, modes="av"), "URL", log=lambda _line: None)
    assert [path.name for path in result.files] == ["Clip.mp4"]
    assert any("audio download failed" in warning for warning in result.warnings)


def test_a_stage_that_produces_nothing_warns(tmp_path, fake):
    fake.produce = {"video": [VIDEO_FILE]}
    result = download(options(tmp_path, modes="av"), "URL", log=lambda _line: None)
    assert any("audio download produced no file" in warning for warning in result.warnings)


def test_a_missing_language_is_only_a_warning(tmp_path, fake):
    fake.tracks = SubtitleTracks(("en",), ("en",))
    fake.produce = {"subs": [SUB_FILE]}
    result = download(options(tmp_path, modes="s", sub_langs=("en", "ja")), "URL", log=lambda _line: None)
    assert any("no ja subtitles" in warning for warning in result.warnings)
    assert result.files


def test_nothing_downloaded_raises(tmp_path, fake):
    fake.fail = {"video"}
    with pytest.raises(AppError, match="Nothing was downloaded"):
        download(options(tmp_path, modes="v"), "URL", log=lambda _line: None)


def test_unreadable_video_info_is_reported(tmp_path, fake):
    fake.tracks = None
    with pytest.raises(AppError, match="Nothing was downloaded"):
        download(options(tmp_path, modes="s"), "URL", log=lambda _line: None)


def test_an_unparsable_subtitle_warns(tmp_path, fake):
    fake.produce = {"subs": [("Clip [dQw4w9WgXcQ].en.srt", "not a subtitle")]}
    with pytest.raises(AppError):
        download(options(tmp_path, modes="s"), "URL", log=lambda _line: None)


def test_no_mode_selected_raises(tmp_path, fake):
    with pytest.raises(AppError, match="no mode selected"):
        download(options(tmp_path, modes=""), "URL", log=lambda _line: None)


def test_a_second_run_does_not_overwrite_the_first(tmp_path, fake):
    fake.produce = {"video": [VIDEO_FILE]}
    settings = options(tmp_path, modes="v")
    download(settings, "URL", log=lambda _line: None)
    result = download(settings, "URL", log=lambda _line: None)
    assert result.files[0].name == "Clip (2).mp4"


def test_the_output_directory_is_created(tmp_path, fake):
    fake.produce = {"video": [VIDEO_FILE]}
    target = tmp_path / "new" / "nested"
    download(options(target, modes="v"), "URL", log=lambda _line: None)
    assert target.is_dir()


def test_cancelling_stops_before_the_next_stage(tmp_path, fake):
    fake.produce = {"subs": [SUB_FILE], "audio": [AUDIO_FILE]}
    with pytest.raises(DownloadCancelled):
        download(options(tmp_path, modes="as"), "URL", log=lambda _line: None, cancelled=lambda: True)
    assert fake.stages_run == []


def test_the_staging_directory_is_cleaned_up(tmp_path, fake):
    fake.produce = {"video": [VIDEO_FILE]}
    download(options(tmp_path, modes="v"), "URL", log=lambda _line: None)
    staging = Path(fake.options_for("video")["outtmpl"]).parent
    assert not staging.exists()


def test_the_log_callback_sees_progress(tmp_path, fake):
    fake.produce = {"video": [VIDEO_FILE]}
    lines: list[str] = []
    download(options(tmp_path, modes="v"), "URL", log=lines.append)
    assert any("[video]" in line for line in lines)
    assert any("saved Clip.mp4" in line for line in lines)


def test_insecure_is_passed_to_yt_dlp(tmp_path, fake):
    fake.produce = {"video": [VIDEO_FILE]}
    download(options(tmp_path, modes="v", insecure=True), "URL", log=lambda _line: None)
    assert fake.options_for("video")["nocheckcertificate"] is True


def test_quality_choices_reach_yt_dlp(tmp_path, fake):
    fake.produce = {"audio": [AUDIO_FILE], "video": [VIDEO_FILE]}
    download(
        options(tmp_path, modes="av", video_quality="720", audio_quality="192", audio_format="opus"),
        "URL",
        log=lambda _line: None,
    )
    assert "[height<=720]" in fake.options_for("video")["format"]
    postprocessor = fake.options_for("audio")["postprocessors"][0]
    assert postprocessor["preferredcodec"] == "opus"
    assert postprocessor["preferredquality"] == "192"


def test_a_ui_can_follow_every_step(tmp_path, fake):
    fake.produce = {"subs": [SUB_FILE], "audio": [AUDIO_FILE]}
    events: list[tuple[str, dict]] = []
    download(
        options(tmp_path, modes="as", sub_formats=("srt",)),
        "URL",
        log=lambda _line: None,
        notify=lambda kind, details: events.append((kind, details)),
    )
    assert events == [
        ("stage", {"stage": "subtitle"}),
        ("saved", {"path": str(tmp_path / "Clip.en.srt")}),
        ("stage", {"stage": "audio"}),
        ("saved", {"path": str(tmp_path / "Clip.mp3")}),
    ]


def test_a_warning_is_also_sent_as_an_event(tmp_path, fake):
    fake.produce = {"video": [VIDEO_FILE]}
    fake.fail = {"audio"}
    events: list[tuple[str, dict]] = []
    download(
        options(tmp_path, modes="av"), "URL", lambda _line: None, None, lambda *event: events.append(event)
    )
    assert ("warning", {"message": "audio download failed: audio boom"}) in events


def test_mp4_asks_for_h264_so_the_file_plays_everywhere(tmp_path, fake):
    fake.produce = {"video": [VIDEO_FILE]}
    download(options(tmp_path, modes="v"), "URL", log=lambda _line: None)
    assert fake.options_for("video")["format_sort"] == ["vcodec:h264"]


def test_our_own_ffmpeg_is_handed_to_yt_dlp(tmp_path, fake):
    fake.produce = {"audio": [AUDIO_FILE], "video": [VIDEO_FILE]}
    fake.ffmpeg = "/cache/ffmpeg"
    download(options(tmp_path, modes="av"), "URL", log=lambda _line: None)
    assert fake.options_for("audio")["ffmpeg_location"] == "/cache/ffmpeg"
    assert fake.options_for("video")["ffmpeg_location"] == "/cache/ffmpeg"


def test_a_system_ffmpeg_is_left_for_yt_dlp_to_find(tmp_path, fake):
    fake.produce = {"audio": [AUDIO_FILE]}
    download(options(tmp_path, modes="a"), "URL", log=lambda _line: None)
    assert "ffmpeg_location" not in fake.options_for("audio")


def test_subtitles_never_wait_for_ffmpeg(tmp_path, fake, monkeypatch):
    def unavailable(job):
        raise AppError("Could not download ffmpeg: offline")

    monkeypatch.setattr(stages, "prepare_ffmpeg", unavailable)
    fake.produce = {"subs": [SUB_FILE], "audio": [AUDIO_FILE]}
    result = download(options(tmp_path, modes="as"), "URL", log=lambda _line: None)

    assert sorted(path.suffix for path in result.files) == [".srt", ".tsv"]
    assert result.warnings == ["audio download failed: Could not download ffmpeg: offline"]
    assert fake.stages_run == ["subs"]


class TestPrepareFfmpeg:
    """The real function, which the `fake` fixture replaces everywhere else."""

    def job(self, tmp_path, cancelled=None, events=None):
        return Job(
            Options(output=str(tmp_path)),
            "URL",
            tmp_path,
            DownloadResult(url="URL"),
            lambda _line: None,
            cancelled,
            (lambda kind, details: events.append((kind, details))) if events is not None else silent,
        )

    def test_download_progress_becomes_a_stage_of_its_own(self, tmp_path, monkeypatch):
        def ensure(log, progress):
            progress(50, 200)
            progress(10, 0)  # no size known: nothing to draw
            return "/cache/ffmpeg"

        monkeypatch.setattr(stages.ffmpeg, "ensure", ensure)
        events: list = []
        assert real_prepare_ffmpeg(self.job(tmp_path, events=events)) == "/cache/ffmpeg"
        assert events == [("progress", {"stage": "ffmpeg", "percent": 25.0})]

    def test_stop_also_stops_the_ffmpeg_download(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stages.ffmpeg, "ensure", lambda log, progress: progress(1, 2))
        with pytest.raises(DownloadCancelled):
            real_prepare_ffmpeg(self.job(tmp_path, cancelled=lambda: True))


def test_stopping_while_ffmpeg_is_fetched_stops_the_job(tmp_path, fake, monkeypatch):
    def stopped(job):
        raise DownloadCancelled("stopped by the user")

    monkeypatch.setattr(stages, "prepare_ffmpeg", stopped)
    fake.produce = {"audio": [AUDIO_FILE]}
    with pytest.raises(DownloadCancelled):
        download(options(tmp_path, modes="a"), "URL", log=lambda _line: None)


def test_known_subtitle_languages_save_the_lookup(tmp_path, fake):
    fake.produce = {"subs": [SUB_FILE]}
    download(options(tmp_path, modes="s"), "URL", log=lambda _line: None, tracks=SubtitleTracks(("en",), ()))
    assert fake.lookups == 0
    download(options(tmp_path, modes="s"), "URL", log=lambda _line: None)
    assert fake.lookups == 1
