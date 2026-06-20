# gen_subtitle Package

Python package behind the bilingual subtitle hands-on app.

## What This Teaches

- splitting a CLI workflow into small modules
- parsing subtitle formats into domain objects
- translating in batches while keeping output deterministic
- writing TSV, SRT, and Markdown study materials
- keeping interactive prompts separate from core processing

## Files To Read First

| File | Role |
| --- | --- |
| `cli.py` | command-line entry point and argument mapping |
| `interactive.py` | guided prompt flow for users who do not want flags |
| `models.py` | subtitle segment and translation data structures |
| `parsers.py` | subtitle parsing |
| `translators.py` | translation backends and batching |
| `writers.py` | TSV, SRT, and Markdown output |
| `youtube.py` | `yt-dlp` integration |

## Hands-on Ideas

1. Add a dry-run mode that prints planned downloads and output names.
2. Add a translator implementation that leaves TODO markers for manual study.
3. Add tests around parsing and writer output before changing formats.
