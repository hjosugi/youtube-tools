<!-- i18n: language-switcher -->
[English](README.md) | [日本語](README.ja.md)

# yt

YouTube **subtitles**, **MP3** and **MP4**, from a page in your browser or one short command.

```bash
yt                 # opens the local web UI: paste a URL, press a button
yt mp3 URL         # or say it in one line
```

`yt` is a Python program, shipped as a standalone binary for Linux, macOS and Windows.

## Install

### Standalone binary (no Python needed)

```bash
# Linux, macOS
curl -fsSL https://raw.githubusercontent.com/hjosugi/youtube-tools/main/install.sh | sh
```

```powershell
# Windows
irm https://raw.githubusercontent.com/hjosugi/youtube-tools/main/install.ps1 | iex
```

The installer puts `yt` in `~/.local/bin` (Windows: `%LOCALAPPDATA%\Programs\yt`), checks the
download against the release's `SHA256SUMS`, adds a **yt** entry to the application menu on
Linux and Windows, and installs the fish and bash completions. Run it again to update.
`YT_INSTALL_DIR` and `YT_VERSION` (for example `v1.1.0`) change where and what it installs.

Or download the file yourself from [Releases](https://github.com/hjosugi/youtube-tools/releases):

| Platform | File |
| --- | --- |
| Linux x86_64 | `yt-linux-x86_64` |
| Linux arm64 | `yt-linux-arm64` |
| macOS Apple Silicon | `yt-macos-arm64` |
| macOS Intel | `yt-macos-x86_64` |
| Windows x86_64 | `yt-windows-x86_64.exe` |

A binary downloaded with a browser on macOS is quarantined by Gatekeeper because it is not
signed; `xattr -d com.apple.quarantine ./yt-macos-arm64` clears that. The installer line
above does not have this problem.

### From source

```bash
cd apps/yt
uv sync
uv run yt
```

### What it needs at run time

- **ffmpeg**, to convert to MP3 and to merge MP4. An ffmpeg on `PATH` is used when there
  is one. Otherwise `yt` downloads a static build the first time audio or video is asked
  for, verifies its SHA-256 and keeps it in its cache directory (`~/.cache/yt` on Linux,
  `~/Library/Caches/yt` on macOS, `%LOCALAPPDATA%\yt\Cache` on Windows; `YT_CACHE_DIR`
  moves it). Subtitles never need ffmpeg.
- **A JavaScript runtime** is optional but recommended: with Deno, Node.js 22+, Bun or
  QuickJS on `PATH`, yt-dlp can solve YouTube's JavaScript challenges and offers every format.

## The web UI

```bash
yt            # also: yt ui, yt --gui
```

A bare `yt` starts a small server on `127.0.0.1` and opens it in your browser.

1. Paste a YouTube URL. The title and the subtitle languages of the video appear.
2. Press **Subtitles**, **MP3**, **MP4** or **All three**.
3. The file shows up under Downloads with a link to its folder.

Good to know:

- **Enter** repeats the last button. Ctrl+V anywhere on the page pastes into the URL box,
  and a link dragged in from another tab works too.
- Several URLs go on separate lines. A playlist URL becomes one download per video; a
  video URL that merely carries `&list=...` downloads that one video.
- **Settings** holds the folder, subtitle languages and formats, video and audio quality
  and file types. Changes are saved at once, to the same config file the command line reads.
- Each download shows, under **Details**, the command that does the same thing, and its log.
- The page follows your browser's language (English or Japanese) and has a switch.

How it runs:

- Started from a terminal, the server lives until Ctrl+C or the **Quit** button. Started
  without one (the application menu entry), it leaves a few minutes after the last tab closes.
- Starting `yt` while it is already running opens the existing page instead of a second server.
- `--port N` picks the port (default 4816, or any free one), `--no-open` skips the browser tab.

Who can use it: the server listens on `127.0.0.1` only. A request must name that address
in its `Host` header, carry a session cookie that is only handed out for the secret in the
start URL, and, to change anything, be same-origin JSON. Other web pages open in the same
browser therefore cannot drive it.

## The command line

```bash
yt [mp3|mp4|sub|all] URL... [options]
```

### What to download

```bash
yt mp3 URL         # audio
yt mp4 URL         # video
yt sub URL         # subtitles
yt all URL         # all three
yt mp3 sub URL     # words combine
yt URL             # whatever the saved default is (subtitles out of the box)
```

`-m` says the same with letters, `a` (audio), `v` (video) and `s` (subtitle): `-m avs`,
`-m av`, `-m all`. Words, URLs and options may come in any order. `yt mp3` without a URL
asks for one.

### Subtitles

English is downloaded unless you say otherwise.

```bash
yt sub URL                  # en
yt sub URL -l en,ja         # English and Japanese
yt sub URL -l all           # every language the video has
yt URL --list-subs          # see what is available before choosing
yt sub URL --no-auto-subs   # human-written captions only
```

Each language is written to its own file, for example `Some Title.en.srt` and `Some Title.ja.srt`.
A language the video does not have is skipped with a note.

Pick the output formats with `-f`. The default is `srt,tsv`.

| Format | Contents |
| --- | --- |
| `srt` | SubRip, ready for video players |
| `vtt` | WebVTT |
| `tsv` | `no` / `start` / `end` / `text` columns, handy in a spreadsheet |
| `txt` | The text only, one line per cue |
| `md` | Markdown with a numbered heading and timestamp per cue |

```bash
yt sub URL -f srt,tsv,md
```

Styling tags such as `<i>` are stripped, and the repeated lines YouTube's auto-captions
produce while scrolling are merged into one cue.

### Quality

```bash
yt mp4 URL --vq 1080              # cap the height at 1080px
yt mp4 URL --vq best --video-format mkv
yt mp3 URL --aq 192               # 192 kbps
yt URL -m a --aq best --audio-format flac
```

| Option | Choices | Default |
| --- | --- | --- |
| `--vq`, `--video-quality` | `best`, `2160`, `1440`, `1080`, `720`, `480`, `360`, `worst` | `best` |
| `--video-format` | `mp4`, `mkv`, `webm` | `mp4` |
| `--aq`, `--audio-quality` | `best`, `320`, `256`, `192`, `128`, `96`, `64` (kbps) | `best` |
| `--audio-format` | `mp3`, `m4a`, `opus`, `flac`, `wav` | `mp3` |

MP4 prefers H.264 video so the file plays everywhere. YouTube has no H.264 above 1080p, so
`--vq 1440` and `--vq 2160` take whichever codec carries that resolution.

### Defaults

Anything you type every time can be saved, including the download directory. The web UI
saves to the same file.

```bash
yt -o ~/Downloads/yt -m avs --vq 1080 --save-config
yt --show-config
yt --config-path
```

| Platform | Config file |
| --- | --- |
| Linux | `~/.config/yt/config.toml` (honours `XDG_CONFIG_HOME`) |
| macOS | `~/Library/Application Support/yt/config.toml` |
| Windows | `%APPDATA%\yt\config.toml` |

Set `YT_CONFIG_FILE` to use a different path. Command-line options always win over the file.
On the command line the default folder is the current directory; in the web UI it is Downloads.

### Guided terminal setup

```bash
yt -i
```

Asks for each option in turn and shows a summary before starting.

### All options

| Option | Meaning |
| --- | --- |
| `mp3`, `mp4`, `sub`, `all` | What to download, as plain words |
| `ui` | Open the web UI (same as a bare `yt`) |
| `-m`, `--mode` | The same as the words: any of `a`, `v`, `s`, or `all` |
| `-l`, `--lang` | Subtitle languages, comma separated, or `all` |
| `-f`, `--sub-format` | Subtitle output formats: `srt`, `vtt`, `tsv`, `txt`, `md` |
| `--no-auto-subs` | Skip auto-generated captions |
| `--vq`, `--video-quality` | Maximum video height |
| `--video-format` | Video container |
| `--aq`, `--audio-quality` | Audio bitrate in kbps |
| `--audio-format` | Audio codec |
| `-o`, `--output` | Output directory |
| `-g`, `--gui`, `--ui` | Open the web UI |
| `--port` | Port for the web UI |
| `--no-open` | Start the web UI without opening a browser tab |
| `-i`, `--interactive` | Guided terminal setup |
| `--list-subs` | Show the available subtitle languages |
| `--save-config` | Store the current options as defaults |
| `--show-config` | Print the effective defaults |
| `--config-path` | Print the config file location |
| `--insecure` | Skip TLS certificate verification (last resort) |
| `--version` | Print the version |

## Shell completion

The installer sets up fish and bash. By hand, from `completions/`:

```bash
# bash
cp completions/yt.bash ~/.local/share/bash-completion/completions/yt

# zsh  (any directory on $fpath)
cp completions/yt.zsh ~/.zsh/completions/_yt

# fish
cp completions/yt.fish ~/.config/fish/completions/yt.fish

# PowerShell
Add-Content $PROFILE ". path\to\completions\yt.ps1"
```

## Development

```bash
uv sync
uv run yt --help
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run python build.py                      # standalone binary into dist/
uv run python smoke.py dist/yt-linux-x86_64 # start the built binary's UI and check it
```

The code lives in `ytcli/`:

| Path | What it holds |
| --- | --- |
| `download/` | Everything that talks to yt-dlp: stages for subtitles, audio and video |
| `subtitles/` | Parsing subtitle files, writing them out, choosing languages |
| `settings/` | Options and the config file |
| `ffmpeg.py` | Finding ffmpeg, or fetching a pinned build |
| `ui/cli.py`, `ui/args.py` | The command line |
| `ui/web/` | The web UI: server, download queue, and the page in `static/` |

### Releases

`build.py` runs PyInstaller for the platform you are on. The release workflow runs it on
five platforms for every `v*` tag, starts each binary's UI as a smoke test, publishes the
binaries with a `SHA256SUMS` file, and then runs the installers against the new release.

```bash
python ../../scripts/bump-version.py minor   # or patch, major, 1.4.2
git commit -am "Release 1.2.0" && git tag v1.2.0 && git push origin main v1.2.0
```

Dependency updates need none of this: Dependabot opens the pull request, CI merges it when
green, and a patch release follows when something inside the binary changed. The one pin
Dependabot cannot see is the ffmpeg build in `ytcli/ffmpeg.py`.

## Notes

- Use this only for content you are allowed to download, and respect YouTube's terms, copyright and rate limits.
- There is no translation feature. `-l en,ja` asks YouTube for the tracks it already publishes.
- Downloaded media, subtitles and cookies must stay out of git.
