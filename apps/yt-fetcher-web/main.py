import sys
import uvicorn

if __name__ == "__main__":
    uvicorn.run("yt_fetcher.web_app:app", host="0.0.0.0", port=8000, reload=True)
