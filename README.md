<!-- i18n: language-switcher -->
[English](README.md) | [日本語](README.ja.md)

# YouTube Tools

One cross-platform tool for YouTube audio, video and subtitles.

Last verified: 2026-09-04

## The tool

| App | Path | Purpose | Runtime |
| --- | --- | --- | --- |
| `yt` | `apps/yt` | CLI and desktop GUI for downloading audio, video and subtitles | Python + uv, or a standalone binary |

Everything lives in one command. `apps/yt/README.md` is the full guide.

## Quick Start

Grab a binary for your platform from [Releases](https://github.com/hjosugi/youtube-tools/releases) — no Python needed — or run from source:

```bash
cd apps/yt
uv sync
uv run yt --help
```

```bash
yt URL                     # English subtitles as .srt and .tsv
yt URL -m avs              # audio, video and subtitles in one run
yt URL -m s -l en,ja       # English and Japanese subtitles
yt URL -m v --vq 1080      # video capped at 1080p
yt URL -m a --aq 192       # audio at 192 kbps
yt --gui                   # desktop window
yt -i                      # guided terminal setup
yt -o ~/Downloads --save-config   # remember a download directory
```

`ffmpeg` must be on your `PATH` for audio extraction and for merging video and audio streams.

## Repository Layout

```text
apps/
  yt/            the tool: CLI, GUI, tests, build script, shell completions
docs/
  consolidation.md
.github/workflows/
  ci.yml         lint and tests on Linux, macOS and Windows
  release.yml    standalone binaries for every platform on a v* tag
```

## History

This repo started as four separate YouTube utilities. They are now one tool — see
[`docs/consolidation.md`](docs/consolidation.md) for what merged, what was dropped, and why.

## Safety And Scope

- Use this only for content you are allowed to access and process.
- Respect YouTube terms, copyright, rate limits, and creator permissions.
- Do not commit downloaded media, subtitles, API keys, cookies, or browser profiles.
- MP3/MP4 extraction depends on `ffmpeg`.

## License

0BSD. You can use, copy, modify, and distribute this project for almost any purpose.
