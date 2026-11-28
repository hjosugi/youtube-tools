# Install or update `yt` on Windows: no Python, no administrator rights.
#
#   irm https://raw.githubusercontent.com/hjosugi/youtube-tools/main/install.ps1 | iex
#
# Run it again to update. Optional settings:
#   $env:YT_INSTALL_DIR  where yt.exe goes            (default: %LOCALAPPDATA%\Programs\yt)
#   $env:YT_VERSION      a release tag such as v1.1.0 (default: the latest release)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'  # the progress bar makes downloads many times slower

$repo = 'hjosugi/youtube-tools'
$asset = 'yt-windows-x86_64.exe'
$dir = if ($env:YT_INSTALL_DIR) { $env:YT_INSTALL_DIR } else { Join-Path $env:LOCALAPPDATA 'Programs\yt' }
$base = if ($env:YT_VERSION) {
    "https://github.com/$repo/releases/download/$($env:YT_VERSION)"
} else {
    "https://github.com/$repo/releases/latest/download"
}

New-Item -ItemType Directory -Force -Path $dir | Out-Null
$target = Join-Path $dir 'yt.exe'
$download = "$target.download"

Write-Host "Downloading $asset..."
Invoke-WebRequest -Uri "$base/$asset" -OutFile $download -UseBasicParsing

# Check the download against the release's checksum list.
$sums = (Invoke-WebRequest -Uri "$base/SHA256SUMS" -UseBasicParsing).Content
if ($sums -is [byte[]]) { $sums = [System.Text.Encoding]::UTF8.GetString($sums) }
$line = ($sums -split "`n") | Where-Object { $_ -match [regex]::Escape($asset) } | Select-Object -First 1
$expected = if ($line) { ($line.Trim() -split '\s+')[0] } else { '' }
$actual = (Get-FileHash -Algorithm SHA256 -Path $download).Hash
if (-not $expected -or $expected -ne $actual) {
    Remove-Item -Force $download
    throw 'The download does not match its checksum. Nothing was installed.'
}

# A running yt.exe cannot be overwritten, but it can be moved out of the way.
if (Test-Path $target) {
    $old = "$target.old"
    Remove-Item -Force $old -ErrorAction SilentlyContinue
    Move-Item -Force $target $old
}
Move-Item -Force $download $target
Remove-Item -Force "$target.old" -ErrorAction SilentlyContinue
Write-Host "Installed $(& $target --version) to $target"

# Start menu entry, so opening the UI needs no terminal at all.
$menu = Join-Path ([Environment]::GetFolderPath('Programs')) 'yt.lnk'
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($menu)
$shortcut.TargetPath = $target
$shortcut.Arguments = 'ui'
$shortcut.Description = 'YouTube subtitles, MP3 and MP4 in one click'
$shortcut.Save()

# Make `yt` work in new terminals.
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (($userPath -split ';') -notcontains $dir) {
    $entries = @($userPath -split ';' | Where-Object { $_ }) + $dir
    [Environment]::SetEnvironmentVariable('Path', ($entries -join ';'), 'User')
    Write-Host "Added $dir to your PATH."
}
if (($env:Path -split ';') -notcontains $dir) { $env:Path += ";$dir" }

# Keep the script out of the executable search path so typing yt still runs yt.exe.
$completionDir = Join-Path $dir 'completions'
New-Item -ItemType Directory -Force -Path $completionDir | Out-Null
$completion = Join-Path $completionDir 'yt.ps1'
if ((& $target --help) -match '--completion') {
    $script = & $target -c pwsh
    if ($LASTEXITCODE -ne 0) { throw 'Could not read the PowerShell completion from yt.exe.' }
    Set-Content -LiteralPath $completion -Encoding UTF8 -Value $script
} else {
    # v1.1.0 and earlier supplied the completer as a release asset.
    Invoke-WebRequest -Uri "$base/yt.ps1" -OutFile $completion -UseBasicParsing
}
. $completion
Write-Host 'PowerShell completion is active. To keep it in new terminals, add this line to $PROFILE:'
Write-Host (". '{0}'" -f $completion.Replace("'", "''"))
Write-Host 'Run: yt'
