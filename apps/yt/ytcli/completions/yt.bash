# Bash completion for yt. To enable now: source <(yt -c bash)
_yt_completion() {
    local cur prev choices match
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    case "$prev" in
        -c|--completion) choices="bash zsh fish pwsh powershell" ;;
        -m|--mode) choices="a v s av as vs avs all audio video subtitle" ;;
        -l|--lang) choices="en ja en,ja all" ;;
        -f|--sub-format) choices="srt vtt tsv txt md srt,tsv srt,tsv,md" ;;
        --vq|--video-quality) choices="best 2160 1440 1080 720 480 360 worst" ;;
        --video-format) choices="mp4 mkv webm" ;;
        --aq|--audio-quality) choices="best 320 256 192 128 96 64" ;;
        --audio-format) choices="mp3 m4a opus flac wav" ;;
        -o|--output)
            compopt -o filenames 2>/dev/null || :
            while IFS= read -r match; do COMPREPLY+=("$match"); done < <(compgen -d -- "$cur")
            return 0 ;;
        --port) return 0 ;;
        *)
            if [[ $cur == -* ]]; then
                choices="-h --help -m --mode -l --lang -f --sub-format --no-auto-subs
                    --vq --video-quality --video-format --aq --audio-quality --audio-format
                    -o --output -i --interactive -g --gui --ui --port --no-open --list-subs --insecure
                    -c --completion --save-config --show-config --config-path --version"
            else
                choices="a v s av as vs avs mp3 mp4 sub all ui"
            fi ;;
    esac
    while IFS= read -r match; do COMPREPLY+=("$match"); done < <(compgen -W "$choices" -- "$cur")
    return 0
}
complete -F _yt_completion yt
