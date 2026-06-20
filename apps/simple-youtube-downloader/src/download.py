import youtube_dl
import ffmpeg
import os
import streamlit as st


@st.cache_data
def download(url, format):
    options = {"nocheckcertificate": True}
    options["outtmpl"] = os.path.join("targetDir", "%(title)s.%(ext)s")
    if format == "mp3":
        options["format"] = "bestaudio[ext=m4a]/bestaudio"
        with youtube_dl.YoutubeDL(options) as ydl:
            ydl.download([url])
            info_dict = ydl.extract_info(url, download=False)
            filename_m4a = (
                ydl.prepare_filename(info_dict)
                .replace(".webm", ".m4a")
                .replace(".mp3", ".m4a")
            )
            return mp4to3(filename_m4a)
    else:
        options["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4"
        with youtube_dl.YoutubeDL(options) as ydl:
            ydl.download([url])
            info_dict = ydl.extract_info(url, download=False)
            filename = ydl.prepare_filename(info_dict)
            return filename.replace(".webm", ".mp4")


def mp4to3(filename):
    root, ext = os.path.splitext(filename)
    if ext not in [".m4a", ".webm"]:
        return filename
    converted_name = f"{root}.mp3"
    stream = ffmpeg.input(filename)
    stream = ffmpeg.output(stream, converted_name, format="mp3", audio_bitrate="128k")
    ffmpeg.run(stream)
    os.remove(filename)
    return converted_name
