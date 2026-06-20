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
