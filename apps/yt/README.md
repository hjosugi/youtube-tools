<!-- i18n: language-switcher -->
[English](README.md) | [日本語](README.ja.md)

# yt

One cross-platform tool for YouTube **a**udio, **v**ideo and **s**ubtitles.

`yt` is a single Python CLI that also ships as a standalone binary for Linux, macOS and Windows,
and opens a desktop window when you would rather click than type.

```bash
yt "https://www.youtube.com/watch?v=..." -m avs
```

## Install

### Standalone binary (no Python needed)

Download the build for your platform from [Releases](https://github.com/hjosugi/youtube-tools/releases):

| Platform | Asset |
| --- | --- |
| Linux x86_64 | `yt-linux-x86_64` |
| macOS Apple Silicon | `yt-macos-arm64` |
| macOS Intel | `yt-macos-x86_64` |
| Windows x86_64 | `yt-windows-x86_64.exe` |

```bash
chmod +x yt-linux-x86_64
sudo mv yt-linux-x86_64 /usr/local/bin/yt
```

On macOS the first run is blocked by Gatekeeper because the binary is unsigned:
`xattr -d com.apple.quarantine ./yt-macos-arm64`.

### From source

```bash
cd apps/yt
uv sync
uv run yt --help
```

`ffmpeg` must be on your `PATH` for audio extraction and for merging video and audio streams.

## Usage

```bash
yt [URL ...] [-m AVS] [-l LANGS] [-f FORMATS] [--vq Q] [--aq Q] [-o DIR]
```

### Choosing what to download

`-m` takes any combination of the letters `a` (audio), `v` (video) and `s` (subtitle):

```bash
yt URL -m s        # subtitles only (the default)
yt URL -m av       # audio and video
yt URL -m avs      # all three in one run
yt URL -m all      # same as -m avs
```

`-m audio,video` and `-m a+v` work too. Without `-m`, `yt` downloads subtitles — change that
permanently with `yt -m av --save-config`.

### Subtitles

Only English is downloaded unless you ask for more:

```bash
yt URL -m s                 # en
yt URL -m s -l en,ja        # English and Japanese
yt URL -m s -l all          # every track the video offers
yt URL --list-subs          # show which languages exist before choosing
yt URL -m s --no-auto-subs  # human-written captions only
```

Each language is written to its own file, e.g. `Some Title.en.srt` and `Some Title.ja.srt`.

Pick the output formats with `-f`; the default is `srt,tsv`:

| Format | What you get |
| --- | --- |
| `srt` | SubRip, ready for any video player |
| `vtt` | WebVTT |
| `tsv` | `no`, `start`, `end`, `text` columns for spreadsheets |
| `txt` | text only, one line per cue |
| `md` | numbered Markdown sections with timestamps |

```bash
yt URL -m s -f srt,tsv,md
```

Formatting tags are stripped and the repeated lines that YouTube's auto-captions scroll through
are collapsed into one cue.

### Quality

```bash
yt URL -m v --vq 1080              # cap the height at 1080p
yt URL -m v --vq best --video-format mkv
yt URL -m a --aq 192               # 192 kbps
yt URL -m a --aq best --audio-format flac
```

| Flag | Choices | Default |
| --- | --- | --- |
| `--vq`, `--video-quality` | `best`, `2160`, `1440`, `1080`, `720`, `480`, `360`, `worst` | `best` |
| `--video-format` | `mp4`, `mkv`, `webm` | `mp4` |
| `--aq`, `--audio-quality` | `best`, `320`, `256`, `192`, `128`, `96`, `64` (kbps) | `best` |
| `--audio-format` | `mp3`, `m4a`, `opus`, `flac`, `wav` | `mp3` |

### Defaults

Save the options you keep retyping, including the download directory:

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

Set `YT_CONFIG_FILE` to point somewhere else. Command-line flags always win over the file.

### GUI mode

```bash
yt --gui
```

A Tk window with the same options: URLs, the audio/video/subtitle checkboxes, subtitle languages
and formats, quality, output directory, a live log and a **Save as defaults** button. Downloads run
in the background so the window stays responsive, and **Stop** cancels them.

The standalone binaries bundle Tk. If you run from a system Python that was built without it,
install `python3-tk` (Debian/Ubuntu), `python3-tkinter` (Fedora) or `tk` (Arch), or use `yt -i`.

### Guided terminal setup

```bash
yt -i
```

Asks for each option in turn and prints a summary before starting. Running `yt` with no arguments
in a terminal does the same.

### All options

| Flag | Description |
| --- | --- |
| `-m`, `--mode` | `a`, `v`, `s` in any combination, or `all` |
| `-l`, `--lang` | subtitle languages, comma separated, or `all` |
| `-f`, `--sub-format` | subtitle formats: `srt`, `vtt`, `tsv`, `txt`, `md` |
| `--no-auto-subs` | skip YouTube's auto-generated captions |
| `--vq`, `--video-quality` | maximum video height |
| `--video-format` | video container |
| `--aq`, `--audio-quality` | audio bitrate in kbps |
| `--audio-format` | audio codec |
| `-o`, `--output` | output directory |
| `-i`, `--interactive` | guided terminal setup |
| `-g`, `--gui` | open the desktop window |
| `--list-subs` | list the subtitle languages a video offers |
| `--save-config` | store the current options as defaults |
| `--show-config` | print the effective defaults |
| `--config-path` | print the config file location |
| `--insecure` | skip TLS certificate verification (last resort) |
| `--version` | print the version |

## Shell completion

Static completions for every shell live in `completions/`:

```bash
# bash
sudo cp completions/yt.bash /usr/share/bash-completion/completions/yt

# zsh  (any directory on $fpath)
sudo cp completions/yt.zsh /usr/local/share/zsh/site-functions/_yt

# fish
cp completions/yt.fish ~/.config/fish/completions/yt.fish

# PowerShell
Add-Content $PROFILE ". path\to\completions\yt.ps1"
```

`./install.sh` copies the binary and the bash/zsh/fish completions in one step on Linux and macOS.

## Development

```bash
uv sync
uv run yt --help
uv run pytest
uv run ruff check .
uv run python build.py        # standalone binary into dist/
```

`build.py` runs PyInstaller for the platform you are on; the release workflow runs it on Linux,
macOS and Windows.

## Notes

- Use this only for content you are allowed to download, and respect YouTube's terms, copyright and rate limits.
- There is no translation feature. `-l en,ja` asks YouTube for the tracks it already publishes.
- Downloaded media, subtitles and cookies must stay out of git.
