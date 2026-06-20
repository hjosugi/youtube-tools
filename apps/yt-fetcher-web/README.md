# YT Fetcher

YT Fetcher is a simple, modern FastAPI web application to download YouTube English subtitles (as TSV), MP3 audio, and MP4 video formats seamlessly.

## Features
- **Batch Processing**: Accepts multiple YouTube URLs separated by newlines.
- **Multiple Formats**: Download English Subtitles (TSV), MP3 (Audio), and MP4 (Video).
- **Single Zip Delivery**: Automatically processes and bundles everything into a single `.zip` file for easy download.
- **Beautiful UI**: Features a modern, dark-themed responsive interface.

## Local Development
To run the server locally:
```bash
# Ensure you have uv installed
uv sync
uv run python main.py
```
> Note: You need `ffmpeg` installed on your host system for MP3 extraction to work locally.

## Deploying to Render
This project is configured out-of-the-box to be deployed on **Render** using Docker.

### Steps to Deploy:
1. Push this repository to your GitHub account.
2. Sign in to your [Render dashboard](https://dashboard.render.com/).
3. Click on **New +** and select **Web Service**.
4. Connect the repository you just pushed.
5. Render will automatically detect the `render.yaml` configuration file and use the `Dockerfile`.
6. Once deployed, Render will spin up the Docker container running the FastAPI web server. Wait for the build to finish, and your app will be online!

> Since it uses Render's free tier, the instance may spin down after 15 minutes of inactivity. When a new request arrives, it will automatically wake up (taking a few seconds).
