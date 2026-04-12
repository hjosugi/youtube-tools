complete -c yt-fetch-cli -f
complete -c yt-fetch-cli -l subtitles -d "Download English subtitles (converted to TSV)"
complete -c yt-fetch-cli -l mp3 -d "Download MP3 audio"
complete -c yt-fetch-cli -l mp4 -d "Download MP4 video"
complete -c yt-fetch-cli -l resolution -x -a "best 1080 720 480 360" -d "MP4 resolution"
complete -c yt-fetch-cli -s o -l output -r -d "Output directory"
complete -c yt-fetch-cli -s h -l help -d "Show help"
