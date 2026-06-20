# yt-fetch-cli

`yt-fetch-cli` is a blazing-fast, strictly native, zero-environment standalone CLI tool for downloading YouTube subtitles, high-quality audio (MP3), and video (MP4) seamlessly.

It bundles the incredible `yt-dlp` engine internally via `PyInstaller`, meaning **you do not need Python or `yt-dlp` installed to run this command**.

## Installation

Go to the [GitHub Releases](../../releases) page and download `yt-fetch-cli` for Linux.

Make it executable and move it to your PATH:
```bash
chmod +x yt-fetch-cli
sudo mv yt-fetch-cli /usr/local/bin/
```
> **Note**: While Python isn't required, you *must* have `ffmpeg` installed on your system (e.g. `sudo apt install ffmpeg`) to extract the MP3 audio formats, as this is standard `yt-dlp` post-processing behavior.

## Features & Usage

Run `yt-fetch-cli` with no arguments for guided setup. You can use it without reading `-h` first.

```bash
yt-fetch-cli
```

The prompt asks for:

1. YouTube URL(s)
2. subtitles / MP3 / MP4
3. MP4 resolution when needed
4. output directory
5. final confirmation

You can still pass everything directly when scripting:

```bash
# Example: Download Subtitles, MP3 and MP4 in 1080p
yt-fetch-cli "https://www.youtube.com/watch?v=..." --subtitles --mp3 --mp4 --resolution 1080
```

### Interactive mode

Run with **no arguments** or `--interactive` and you'll be guided through the options:

```bash
$ yt-fetch-cli
YouTube Fetcher interactive setup
YouTube URL(s), separated by spaces: https://www.youtube.com/watch?v=...
Subtitles as TSV [Y/n]:
MP3 audio [y/N]: y
MP4 video [y/N]:
Output directory [.]: downloads
Start download [Y/n]:
```

You can paste multiple space-separated URLs at the prompt.

### Options

| Flag | Description |
| ---- | ----------- |
| `--subtitles` | Downloads auto & manual English subtitles, outputs explicitly to `.tsv`. |
| `--mp3` | Downloads the highest quality audio globally and extracts it to MP3. |
| `--mp4` | Downloads the video and merges with highest quality audio inline. |
| `--resolution` | Limits the maximum height. Choices: `best, 1080, 720, 480, 360` (Default: `best`) |
| `-o`, `--output` | Destination directory. (Default: `./` current directory) |

---
### Auto-Completion

We provide manual, incredibly snappy static autocomplete hooks for `bash` and `fish` located in the `completions/` folder in the repo. Simply source them into your shell profile (`~/.bashrc` / `~/.config/fish/config.fish`) to unlock `[Tab]` autocompletes.

## Development

If you're modifying this tool, install [`uv`](https://docs.astral.sh/uv/) and run:
```bash
# Install dependencies
uv sync

# Run the cli wrapper normally
uv run python cli.py

# Test the interactive prompt flow without downloading
uv run python test_interactive.py

# Bump the version automatically (Requires Git clean tree)
# e.g., bumps package logic string, commits cleanly, sets tag logic natively
uvx bump-my-version bump patch # (or minor, major) 

# Build locally via PyInstaller
./build.sh
```
