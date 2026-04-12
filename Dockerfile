FROM python:3.11-slim

# Install ffmpeg for yt-dlp to extract audio/video
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen

# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 8000

# Start server (Render overrides PORT)
CMD ["sh", "-c", "uv run uvicorn yt_fetcher.web_app:app --host 0.0.0.0 --port ${PORT:-8000}"]
