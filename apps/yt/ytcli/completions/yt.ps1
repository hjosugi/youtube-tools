# PowerShell completion for yt. To enable now: yt -c pwsh | Out-String | Invoke-Expression

Register-ArgumentCompleter -Native -CommandName yt,yt.exe -ScriptBlock {
    param([string]$wordToComplete, $commandAst, $cursorPosition)

    $previousToken = $commandAst.CommandElements |
        Where-Object { $_.Extent.EndOffset -lt $cursorPosition } | Select-Object -Last 1
    $previous = [string]$previousToken.Extent.Text

    $valuesByFlag = @{
        '-c'              = 'bash', 'zsh', 'fish', 'pwsh', 'powershell'
        '--completion'    = 'bash', 'zsh', 'fish', 'pwsh', 'powershell'
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

    if ($previous -in '-o', '--output') {
        return [System.Management.Automation.CompletionCompleters]::CompleteFilename($wordToComplete) |
            Where-Object ResultType -eq ProviderContainer
    }
    if ($previous -eq '--port') { return }

    $type = 'ParameterValue'
    if ($valuesByFlag.ContainsKey($previous)) {
        $choices = $valuesByFlag[$previous]
    } elseif ($wordToComplete.StartsWith('-')) {
        $type = 'ParameterName'
        $choices = @(
            '-h', '--help', '-m', '--mode', '-l', '--lang', '-f', '--sub-format', '--no-auto-subs',
            '--vq', '--video-quality', '--video-format', '--aq', '--audio-quality', '--audio-format',
            '-o', '--output', '-i', '--interactive', '-g', '--gui', '--ui', '--port', '--no-open',
            '--list-subs', '--insecure', '-c', '--completion', '--save-config', '--show-config', '--config-path', '--version'
        )
    } else {
        $choices = 'a', 'v', 's', 'av', 'as', 'vs', 'avs', 'mp3', 'mp4', 'sub', 'all', 'ui'
    }
    $choices |
        Where-Object { $_.StartsWith($wordToComplete, [StringComparison]::OrdinalIgnoreCase) } |
        ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, $type, $_) }
}
