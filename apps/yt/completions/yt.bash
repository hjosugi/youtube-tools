# bash completion for yt
# install: cp yt.bash /usr/share/bash-completion/completions/yt

_yt_completion() {
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    local opts="-h --help -m --mode -l --lang -f --sub-format --no-auto-subs
        --vq --video-quality --video-format --aq --audio-quality --audio-format
        -o --output -i --interactive -g --gui --list-subs --insecure
        --save-config --show-config --config-path --version"

    case "${prev}" in
        -m|--mode)
            COMPREPLY=( $(compgen -W "a v s av as vs avs all audio video subtitle" -- "${cur}") )
            return 0 ;;
        -l|--lang)
            COMPREPLY=( $(compgen -W "en ja en,ja all" -- "${cur}") )
            return 0 ;;
        -f|--sub-format)
            COMPREPLY=( $(compgen -W "srt vtt tsv txt md srt,tsv srt,tsv,md" -- "${cur}") )
            return 0 ;;
        --vq|--video-quality)
            COMPREPLY=( $(compgen -W "best 2160 1440 1080 720 480 360 worst" -- "${cur}") )
            return 0 ;;
        --video-format)
            COMPREPLY=( $(compgen -W "mp4 mkv webm" -- "${cur}") )
            return 0 ;;
        --aq|--audio-quality)
            COMPREPLY=( $(compgen -W "best 320 256 192 128 96 64" -- "${cur}") )
            return 0 ;;
        --audio-format)
            COMPREPLY=( $(compgen -W "mp3 m4a opus flac wav" -- "${cur}") )
            return 0 ;;
        -o|--output)
            compopt -o dirnames 2>/dev/null
            COMPREPLY=( $(compgen -d -- "${cur}") )
            return 0 ;;
    esac

    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
    fi
    return 0
}
complete -F _yt_completion yt
