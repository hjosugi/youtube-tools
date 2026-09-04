#compdef yt
# zsh completion for yt
# install: cp yt.zsh <any dir on $fpath>/_yt

_yt() {
    _arguments -s -S \
        '(-h --help)'{-h,--help}'[show help]' \
        '(-m --mode)'{-m,--mode}'[what to download: a, v, s, or all]:mode:(a v s av as vs avs all)' \
        '(-l --lang)'{-l,--lang}'[subtitle languages, comma separated, or all]:languages:(en ja en,ja all)' \
        '(-f --sub-format)'{-f,--sub-format}'[subtitle output formats]:formats:(srt vtt tsv txt md srt,tsv)' \
        '--no-auto-subs[skip YouTube auto-generated captions]' \
        '(--vq --video-quality)'{--vq,--video-quality}'[maximum video height]:quality:(best 2160 1440 1080 720 480 360 worst)' \
        '--video-format[video container]:container:(mp4 mkv webm)' \
        '(--aq --audio-quality)'{--aq,--audio-quality}'[audio bitrate in kbps]:quality:(best 320 256 192 128 96 64)' \
        '--audio-format[audio codec]:codec:(mp3 m4a opus flac wav)' \
        '(-o --output)'{-o,--output}'[output directory]:directory:_files -/' \
        '(-i --interactive)'{-i,--interactive}'[guided terminal setup]' \
        '(-g --gui)'{-g,--gui}'[open the desktop window]' \
        '--list-subs[list the subtitle languages a video offers]' \
        '--insecure[skip TLS certificate verification]' \
        '--save-config[store the current options as defaults]' \
        '--show-config[print the effective defaults]' \
        '--config-path[print the config file location]' \
        '--version[print the version]' \
        '*:url:_urls'
}

_yt "$@"
