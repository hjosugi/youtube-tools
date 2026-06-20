# yt_fetcher Web Package

FastAPI package used by the browser-based YouTube fetcher.

## What This Teaches

- exposing a small download workflow over HTTP
- handling multiple YouTube URLs as a batch
- producing downloadable artifacts from temporary work directories
- reusing parsing and writer code from a CLI-shaped workflow
- keeping the web boundary thin around the core fetch logic

## Files To Read First

| File | Role |
| --- | --- |
| `web_app.py` | FastAPI routes and response flow |
| `models.py` | request and result data structures |
| `parsers.py` | subtitle parsing helpers |
| `writers.py` | output file generation |
| `youtube.py` | `yt-dlp` integration |
| `utils.py` | filesystem and archive helpers |

## Hands-on Ideas

1. Add a status endpoint for long-running jobs.
2. Add input validation for duplicate or malformed URLs.
3. Extract shared code with the CLI package after writing characterization tests.
