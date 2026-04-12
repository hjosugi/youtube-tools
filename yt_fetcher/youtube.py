import time
from pathlib import Path
import yt_dlp

from yt_fetcher.models import AppError

def download_media(url: str, out_dir: Path, dl_sub: bool, dl_mp3: bool, dl_mp4: bool, resolution: str = "best") -> tuple[Path | None, Path | None, Path | None]:
    out_dir.mkdir(parents=True, exist_ok=True)
    base_opts = {
        'outtmpl': str(out_dir / '%(title)s [%(id)s].%(ext)s'),
        'ignoreconfig': True,
        'updatetime': False, # equivalent to --no-mtime
        'quiet': False,
    }

    if dl_sub:
        sub_opts = base_opts.copy()
        sub_opts.update({
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en.*'],
            'subtitlesformat': 'srt/vtt/best',
            'skip_download': True,
        })
        try:
            with yt_dlp.YoutubeDL(sub_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"Subtitle download warning/error: {e}")
        
    if dl_mp3 or dl_mp4:
        media_opts = base_opts.copy()
        format_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        if resolution != "best":
            format_str = f"bestvideo[height<={resolution}][ext=mp4]+bestaudio[ext=m4a]/best[height<={resolution}][ext=mp4]/best"
        media_opts['format'] = format_str

        postprocessors = []
        if dl_mp3:
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            })
            if dl_mp4:
                media_opts['keepvideo'] = True
                
        if postprocessors:
            media_opts['postprocessors'] = postprocessors

        try:
            with yt_dlp.YoutubeDL(media_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            print(f"Media download warning/error: {e}")

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
