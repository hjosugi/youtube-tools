# PowerShell completion for yt
# install: Add-Content $PROFILE ". path\to\yt.ps1"

Register-ArgumentCompleter -Native -CommandName yt -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $tokens = $commandAst.CommandElements | ForEach-Object { $_.ToString() }
    $previous = if ($tokens.Count -ge 2) { $tokens[$tokens.Count - 2] } else { '' }

    $valuesByFlag = @{
        '-m'              = 'a', 'v', 's', 'av', 'as', 'vs', 'avs', 'all'
        '--mode'          = 'a', 'v', 's', 'av', 'as', 'vs', 'avs', 'all'
        '-l'              = 'en', 'ja', 'en,ja', 'all'
        '--lang'          = 'en', 'ja', 'en,ja', 'all'
        '-f'              = 'srt', 'vtt', 'tsv', 'txt', 'md', 'srt,tsv'
        '--sub-format'    = 'srt', 'vtt', 'tsv', 'txt', 'md', 'srt,tsv'
        '--vq'            = 'best', '2160', '1440', '1080', '720', '480', '360', 'worst'
        '--video-quality' = 'best', '2160', '1440', '1080', '720', '480', '360', 'worst'
        '--video-format'  = 'mp4', 'mkv', 'webm'
        '--aq'            = 'best', '320', '256', '192', '128', '96', '64'
        '--audio-quality' = 'best', '320', '256', '192', '128', '96', '64'
        '--audio-format'  = 'mp3', 'm4a', 'opus', 'flac', 'wav'
    }

    if ($valuesByFlag.ContainsKey($previous)) {
        return $valuesByFlag[$previous] |
            Where-Object { $_ -like "$wordToComplete*" } |
            ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }
    }

    $flags = @(
        '--help', '--mode', '--lang', '--sub-format', '--no-auto-subs',
        '--vq', '--video-quality', '--video-format', '--aq', '--audio-quality', '--audio-format',
        '--output', '--interactive', '--gui', '--list-subs', '--insecure',
        '--save-config', '--show-config', '--config-path', '--version'
    )
    $flags |
        Where-Object { $_ -like "$wordToComplete*" } |
        ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterName', $_) }
}
