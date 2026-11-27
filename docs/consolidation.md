<!-- i18n: language-switcher -->
[English](consolidation.md) | [日本語](consolidation.ja.md)

# Consolidation Notes

Date: 2026-06-20

This repo consolidates:

- `hjosugi/youtube-bilingual-subtitle`
- `hjosugi/yt-fetcher`
- `hjosugi/yt-fetcher-cli`
- `hjosugi/simple-youtube-downloader`

The original programs are intentionally kept as separate apps:

- `youtube-bilingual-subtitle` becomes `apps/bilingual-subtitle`
- `yt-fetcher` becomes `apps/yt-fetcher-web`
- `yt-fetcher-cli` becomes `apps/yt-fetcher-cli`
- `simple-youtube-downloader` becomes `apps/simple-youtube-downloader`

## Why

- all three are YouTube utility projects
- all three are Python/uv projects
- they share safety, copyright, ffmpeg, yt-dlp, and output-file concerns
- keeping three public repositories makes the GitHub profile noisier than the topic deserves

## Non-goals

- do not force one CLI or one package name yet
- do not deduplicate `yt_fetcher` modules until tests exist
- do not mix web deployment config with CLI release config

## Follow-up

1. Add smoke tests for each app.
2. Add `.env.example` for translation providers if DeepL stays supported.
3. Review dependency baselines app by app.
4. Add GitHub Actions after the commands are stable.

---

# Merge Into One Tool

Date: 2026-09-04

The four apps became one command: `apps/yt`, installed as `yt`.

## What moved where

| Old app | Replaced by |
| --- | --- |
| `apps/yt-fetcher-cli` | `yt` — same job, plus language and format selection, quality flags, saved defaults |
| `apps/bilingual-subtitle` | `yt -m s -l en,ja` — YouTube's own tracks instead of a translation engine |
| `apps/yt-fetcher-web` | `yt --gui` — a desktop window instead of a FastAPI server |
| `apps/simple-youtube-downloader` | `yt` — the Streamlit experiment is no longer maintained |

`launcher.py` is gone; `yt` with no arguments starts the guided setup and `yt --gui` opens the window.

## What was dropped

- **Translation.** `DeepLTranslator` and `ArgosTranslator`, `DEEPL_AUTH_KEY`, and the bilingual
  TSV/SRT/Markdown writers. `-l en,ja` now asks YouTube for the tracks it already publishes, so no
  API key, no model download, and no translation cost.
- **The web server.** No FastAPI, no Dockerfile, no `render.yaml` / `fly.toml` / `Procfile`.
  A single-user download tool did not need a deployment target.
- **Three duplicated copies of `yt_fetcher`.** One `ytcli` package now, with tests.

## What changed in behaviour

- `--subtitles/--mp3/--mp4` became `-m` with the letters `a`, `v` and `s`.
- Subtitle languages are resolved against the tracks a video actually has. The old `en.*` pattern
  also matched YouTube's machine-translated tracks (`en-de`, `en-fr`, ...), which returned HTTP 429.
- Subtitles can be written as `srt`, `vtt`, `tsv`, `txt` or `md`; the old CLI only wrote `tsv`.
- Video and audio are fetched in separate passes into a temporary directory, so results are found
  by location rather than by guessing from modification times.
- TLS certificates are verified using `certifi` instead of being switched off in frozen builds.
  `--insecure` is opt-in.
- Defaults, including the download directory, live in a config file (`yt --config-path`).

## Follow-up from the previous round

1. ~~Add smoke tests for each app.~~ Done: 83 tests in `apps/yt/tests`.
2. ~~Add `.env.example` for translation providers if DeepL stays supported.~~ Dropped with translation.
3. ~~Review dependency baselines app by app.~~ One project, current `yt-dlp`, `certifi`, `pytest`, `ruff`, `pyinstaller`.
4. ~~Add GitHub Actions after the commands are stable.~~ Done: `ci.yml` and `release.yml` at the repo root.
   The old workflow lived in `apps/yt-fetcher-cli/.github/workflows/`, where GitHub never ran it.

---

# A Web UI Instead Of Commands

Date: 2026-11-27

The tool worked, but using it meant remembering `-m a`, installing ffmpeg first and, for the
window, having a Python with Tk. This round removes those three hurdles.

## What changed

| Before | Now |
| --- | --- |
| `yt --gui` opened a Tk window | A bare `yt` opens a page in the browser, served on `127.0.0.1` |
| `yt URL -m a` | `yt mp3 URL` (also `mp4`, `sub`, `all`); `-m` still works |
| A bare `yt` in a terminal started the question-by-question wizard | The wizard is `yt -i` |
| ffmpeg had to be installed before MP3 or MP4 worked | Without one, a pinned static build is downloaded on first use |
| Download a binary, `chmod +x`, move it into `PATH` | `curl ... install.sh \| sh`, or `irm ... install.ps1 \| iex` |
| Dependencies were updated by hand | Dependabot, merged by CI, released automatically |

## Why a page in the browser

- Tk is missing from many Python builds, NixOS and uv's among them, so the window did not
  open on the machine the tool is developed on. A browser is always there.
- The page needs nothing beyond the standard library's `http.server`, so the binary lost
  Tcl/Tk rather than gaining a GUI toolkit.
- It is the `duckdb -ui` model: one program, and the UI is just another way to call it.
  The page shows the equivalent command under every download.

## Smaller changes in behaviour

- MP4 prefers H.264 up to 1080p, so the file plays in every player. It used to pick AV1
  whenever YouTube offered it.
- A watch URL that carries `&list=...` downloads that one video. A playlist URL is expanded
  into its videos, and subtitles now work for playlists as well.
- yt-dlp is installed with its `default` and `curl-cffi` extras and is told about every
  JavaScript runtime on `PATH`, not only Deno. This removes the "formats may be missing"
  and "no impersonate target" warnings.
- Release binaries now also exist for Linux arm64, and come with a `SHA256SUMS` file.
- `[tool.bumpversion]` gave way to `scripts/bump-version.py`, which needs nothing installed
  and also updates `uv.lock`.

## What was dropped

- The Tk window (`ytcli/ui/gui`). The web UI replaces it on every platform.
- `apps/yt/install.sh`, which installed a locally built binary with `sudo`. The installers
  at the repository root download the release and need no root.
