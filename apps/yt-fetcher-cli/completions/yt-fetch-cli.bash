_yt_fetch_cli_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    opts="--subtitles --mp3 --mp4 --resolution --output -o -h --help"

    case "${prev}" in
        --resolution)
            local res="best 1080 720 480 360"
            COMPREPLY=( $(compgen -W "${res}" -- ${cur}) )
            return 0
            ;;
        -o|--output)
            compopt -o default
            COMPREPLY=( $(compgen -d -- ${cur}) )
            return 0
            ;;
        *)
            ;;
    esac

    if [[ ${cur} == -* ]] ; then
        COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
        return 0
    fi
}
complete -F _yt_fetch_cli_completion yt-fetch-cli
