# fish completion for yt
# install: cp yt.fish ~/.config/fish/completions/yt.fish

complete -c yt -f
complete -c yt -s h -l help -d "Show help"
complete -c yt -s m -l mode -x -a "a v s av as vs avs all" -d "What to download (a/v/s)"
complete -c yt -s l -l lang -x -a "en ja en,ja all" -d "Subtitle languages"
complete -c yt -s f -l sub-format -x -a "srt vtt tsv txt md srt,tsv" -d "Subtitle output formats"
complete -c yt -l no-auto-subs -d "Skip auto-generated captions"
complete -c yt -l vq -l video-quality -x -a "best 2160 1440 1080 720 480 360 worst" -d "Maximum video height"
complete -c yt -l video-format -x -a "mp4 mkv webm" -d "Video container"
complete -c yt -l aq -l audio-quality -x -a "best 320 256 192 128 96 64" -d "Audio bitrate (kbps)"
complete -c yt -l audio-format -x -a "mp3 m4a opus flac wav" -d "Audio codec"
complete -c yt -s o -l output -r -F -d "Output directory"
complete -c yt -s i -l interactive -d "Guided terminal setup"
complete -c yt -s g -l gui -d "Open the desktop window"
complete -c yt -l list-subs -d "List the subtitle languages a video offers"
complete -c yt -l insecure -d "Skip TLS certificate verification"
complete -c yt -l save-config -d "Store the current options as defaults"
complete -c yt -l show-config -d "Print the effective defaults"
complete -c yt -l config-path -d "Print the config file location"
complete -c yt -l version -d "Print the version"
