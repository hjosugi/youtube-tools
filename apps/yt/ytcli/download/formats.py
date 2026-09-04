from __future__ import annotations


def build_video_format(quality: str, container: str) -> str:
    """Build the yt-dlp format string for a height cap and a container preference."""
    video_ext = "[ext=mp4]" if container == "mp4" else ""
    audio_ext = "[ext=m4a]" if container == "mp4" else ""
    if quality == "worst":
        return f"worstvideo{video_ext}+worstaudio{audio_ext}/worstvideo+worstaudio/worst"
    if quality == "best":
        return f"bestvideo{video_ext}+bestaudio{audio_ext}/bestvideo+bestaudio/best"
    height = f"[height<={quality}]"
    return f"bestvideo{height}{video_ext}+bestaudio{audio_ext}/bestvideo{height}+bestaudio/best{height}/best"


def build_audio_quality(quality: str) -> str:
    """yt-dlp reads "0" as best VBR and any other number as a target bitrate in kbps."""
    return "0" if quality == "best" else quality
