import shutil
import time
from pathlib import Path

from yt_fetcher.models import AppError
from yt_fetcher.utils import run

def choose_yt_dlp_command() -> list[str]:
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    if shutil.which("uvx"):
        return ["uvx", "yt-dlp"]
    if shutil.which("uv"):
        return ["uv", "tool", "run", "yt-dlp"]
    return ["yt-dlp"]

def download_media(url: str, out_dir: Path, dl_sub: bool, dl_mp3: bool, dl_mp4: bool, resolution: str = "best") -> tuple[Path | None, Path | None, Path | None]:
    out_dir.mkdir(parents=True, exist_ok=True)
    before = time.time() - 1.0

    # Split subtitle download and media download to avoid yt-dlp post-processing 
    # (like --embed-subs global configs or ffmpeg crashes) from wiping out the .srt files.
    cmd_base = choose_yt_dlp_command() + ["--ignore-config", "--no-mtime", "-P", str(out_dir)]

    if dl_sub:
        sub_cmd = cmd_base + [
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs", "en.*",
            "--sub-format", "srt/vtt/best",
            "--skip-download",
            url
        ]
        run(sub_cmd)
        
    if dl_mp3 or dl_mp4:
        media_cmd = cmd_base.copy()
        format_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        if resolution != "best":
            format_str = f"bestvideo[height<={resolution}][ext=mp4]+bestaudio[ext=m4a]/best[height<={resolution}][ext=mp4]/best"
            
        if dl_mp3 and dl_mp4:
            media_cmd.extend([
                "-f", format_str,
                "-x", "--audio-format", "mp3", "--keep-video"
            ])
        elif dl_mp3:
            media_cmd.extend([
                "-x", "--audio-format", "mp3"
            ])
        elif dl_mp4:
            media_cmd.extend([
                "-f", format_str
            ])
        media_cmd.append(url)
        run(media_cmd)

    sub_path, mp3_path, mp4_path = None, None, None
    candidates = sorted(
        [p for p in out_dir.iterdir() if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    for p in candidates:
        suffix = p.suffix.lower()
        if dl_sub and not sub_path and suffix in ('.srt', '.vtt'):
            sub_path = p
        elif dl_mp3 and not mp3_path and suffix == '.mp3':
            mp3_path = p
        elif dl_mp4 and not mp4_path and suffix == '.mp4':
            mp4_path = p

    files_in_dir = [p.name for p in out_dir.iterdir()]
    if dl_sub and not sub_path:
        raise AppError(f"Subtitle file not found. The video might not have English subtitles. Files found: {files_in_dir}")
    if dl_mp3 and not mp3_path:
        raise AppError(f"MP3 audio file could not be generated. yt-dlp might have failed. Files found: {files_in_dir}")
    if dl_mp4 and not mp4_path:
        raise AppError(f"MP4 video file could not be generated. yt-dlp might have failed. Files found: {files_in_dir}")
        
    return sub_path, mp3_path, mp4_path
