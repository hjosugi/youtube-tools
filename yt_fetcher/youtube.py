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

def download_media(url: str, out_dir: Path, dl_sub: bool, dl_mp3: bool, dl_mp4: bool) -> tuple[Path | None, Path | None, Path | None]:
    out_dir.mkdir(parents=True, exist_ok=True)
    before = time.time() - 1.0

    cmd = choose_yt_dlp_command()
    
    if dl_sub:
        cmd.extend([
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs", "en.*",
            "--sub-format", "srt/vtt/best",
        ])
        
    if dl_mp3 and dl_mp4:
        cmd.extend([
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-x", "--audio-format", "mp3", "--keep-video"
        ])
    elif dl_mp3:
        cmd.extend([
            "-x", "--audio-format", "mp3"
        ])
    elif dl_mp4:
        cmd.extend([
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        ])
    else:
        if dl_sub:
            cmd.append("--skip-download")
        else:
            return None, None, None
        
    cmd.extend(["--no-mtime", "-P", str(out_dir), url])
    run(cmd)

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

    if dl_sub and not sub_path:
        raise AppError("Subtitle file not found. The video might not have English subtitles.")
        
    return sub_path, mp3_path, mp4_path
