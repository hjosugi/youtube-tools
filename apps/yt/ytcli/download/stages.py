from __future__ import annotations

import shutil
from pathlib import Path

from ..models import AppError, DownloadCancelled
from ..subtitles import SUBTITLE_WRITERS, parse_subtitle_file, resolve_subtitle_langs
from ..utils import base_stem, language_of, unique_path
from .client import list_subtitles, run_download
from .formats import build_audio_quality, build_video_format
from .job import Job

SUBTITLE_SUFFIXES = (".srt", ".vtt", ".webvtt")


def fetch_subtitles(job: Job) -> None:
    """Download the resolved subtitle tracks and write them in every requested format."""
    options = job.options
    job.log(f"[subtitle] requested: {', '.join(options.sub_langs)}")

    try:
        tracks = list_subtitles(job.url, insecure=options.insecure)
    except AppError as error:
        job.warn(str(error))
        return

    codes, warnings = resolve_subtitle_langs(options.sub_langs, tracks, options.auto_subs)
    for warning in warnings:
        job.warn(warning)
    if not codes:
        return

    work_dir = job.stage_dir("subs")
    ydl_options = job.ydl_options(work_dir)
    ydl_options.update(
        {
            "skip_download": True,
            "writesubtitles": True,
            # Only ask for auto-captions when a resolved code is not a human-written track.
            "writeautomaticsub": options.auto_subs
            and any(code not in tracks.manual for code in codes),
            "subtitleslangs": codes,
            "subtitlesformat": "srt/vtt/best",
        }
    )
    job.log(f"  downloading: {', '.join(codes)}")
    if not run_stage(job, ydl_options, "subtitle"):
        return

    sources = [path for path in files_in(work_dir) if path.suffix.lower() in SUBTITLE_SUFFIXES]
    if not sources:
        job.warn(f"no subtitle file was produced for: {', '.join(codes)}")
        return
    for source in sources:
        convert_subtitle(job, source)


def convert_subtitle(job: Job, source: Path) -> None:
    """Turn one downloaded .srt/.vtt into the formats the user asked for."""
    language = language_of(source)
    try:
        cues = parse_subtitle_file(source)
    except AppError as error:
        job.warn(str(error))
        return
    stem = base_stem(source, language)
    suffix = f".{language}" if language else ""
    for fmt in job.options.sub_formats:
        target = unique_path(job.options.out_dir / f"{stem}{suffix}.{fmt}")
        SUBTITLE_WRITERS[fmt](cues, target)
        job.save(target, f" ({len(cues)} lines)")


def fetch_media(job: Job, kind: str) -> None:
    """Download audio or video in its own pass, then move the result to the output directory."""
    work_dir = job.stage_dir(kind)
    ydl_options = job.ydl_options(work_dir)
    ydl_options.update(media_options(job, kind))

    if not run_stage(job, ydl_options, kind):
        return

    produced = files_in(work_dir)
    if not produced:
        job.warn(f"{kind} download produced no file")
        return
    for source in produced:
        target = unique_path(job.options.out_dir / f"{base_stem(source)}{source.suffix}")
        shutil.move(str(source), str(target))
        job.save(target)


def media_options(job: Job, kind: str) -> dict:
    """The yt-dlp options that differ between an audio pass and a video pass."""
    options = job.options
    if kind == "audio":
        job.log(f"[audio] {options.audio_format} @ {options.audio_quality}")
        return {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": options.audio_format,
                    "preferredquality": build_audio_quality(options.audio_quality),
                }
            ],
        }
    job.log(f"[video] {options.video_format} @ {options.video_quality}")
    return {
        "format": build_video_format(options.video_quality, options.video_format),
        "merge_output_format": options.video_format,
    }


def run_stage(job: Job, ydl_options: dict, kind: str) -> bool:
    """Run one yt-dlp pass, turning any failure into a warning. True when it ran."""
    try:
        run_download(ydl_options, job.url)
    except DownloadCancelled:
        raise
    except Exception as error:  # yt-dlp and ffmpeg raise a wide range of errors
        job.warn(f"{kind} download failed: {error}")
        return False
    return True


def files_in(directory: Path) -> list[Path]:
    """Every file a stage produced, in a stable order."""
    return sorted(path for path in directory.rglob("*") if path.is_file())
