# YouTube Tools

Small YouTube utility apps kept together as one learning and maintenance repo.

Last verified: 2026-06-20

## Apps

| App | Path | Purpose | Runtime |
| --- | --- | --- | --- |
| Bilingual subtitle generator | `apps/bilingual-subtitle` | Download English YouTube subtitles and generate bilingual English/Japanese TSV, SRT, and Markdown files | Python + uv |
| YT Fetcher web | `apps/yt-fetcher-web` | FastAPI web UI for batch subtitle, MP3, and MP4 downloads | Python + uv + FastAPI |
| YT Fetcher CLI | `apps/yt-fetcher-cli` | Standalone-oriented CLI for subtitles, MP3, and MP4 downloads | Python + uv + PyInstaller |
| Simple YouTube downloader | `apps/simple-youtube-downloader` | Older Streamlit downloader experiment kept for reference and modernization | Python + Streamlit |

These apps do not need to become one program. The repo groups them because they share the same problem area, maintenance concerns, and safety notes.

## Repository Layout

```text
apps/
  bilingual-subtitle/
  simple-youtube-downloader/
  yt-fetcher-web/
  yt-fetcher-cli/
docs/
  consolidation.md
```

Each app keeps its own `pyproject.toml`, `uv.lock`, README, and commands. Work from the app directory unless a root-level task says otherwise.

## Quick Start

```bash
cd apps/bilingual-subtitle
uv sync
uv run python main.py "https://www.youtube.com/watch?v=..."
```

```bash
cd apps/yt-fetcher-web
uv sync
uv run python main.py
```

```bash
cd apps/yt-fetcher-cli
uv sync
uv run python cli.py "https://www.youtube.com/watch?v=..." --subtitles
```

```bash
cd apps/simple-youtube-downloader
pip install -r requirements.txt
streamlit run src/main.py
```

## Safety And Scope

- Use these tools only for content you are allowed to access and process.
- Respect YouTube terms, copyright, rate limits, and creator permissions.
- Do not commit downloaded media, subtitles, API keys, cookies, or browser profiles.
- MP3/MP4 extraction depends on `ffmpeg`.
- DeepL translation requires `DEEPL_AUTH_KEY` when using the DeepL translator path.

## Maintenance Notes

- Keep each app runnable on its own before sharing code.
- If common code becomes meaningful, move it to `packages/` after there are tests.
- Prefer small documented commands over a clever root orchestrator.
- Update app READMEs when command behavior changes.
- Modernize `apps/simple-youtube-downloader` before treating it as a maintained app.
