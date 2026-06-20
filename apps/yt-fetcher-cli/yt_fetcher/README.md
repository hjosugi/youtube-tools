# yt_fetcher CLI Package

Core Python package used by the standalone `yt-fetch-cli` app.

## What This Teaches

- building a useful CLI that can also guide users interactively
- keeping download options as typed data instead of raw argument strings
- separating `yt-dlp` calls from parsing and output formatting
- writing small modules that can later be packaged into a single binary

## Files To Read First

| File | Role |
| --- | --- |
| `interactive.py` | prompt-first flow for normal users |
| `models.py` | download option data structures |
| `parsers.py` | URL and subtitle parsing helpers |
| `writers.py` | subtitle TSV output |
| `youtube.py` | `yt-dlp` command construction |
| `utils.py` | shared filesystem and text helpers |

## Hands-on Ideas

1. Add a preview step that shows the exact planned downloads.
2. Add a new output format while keeping `youtube.py` focused on fetching.
3. Add a parser test for multiple URL input.
