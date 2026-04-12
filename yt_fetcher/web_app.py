import shutil
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from yt_fetcher.parsers import parse_subtitle_file
from yt_fetcher.utils import base_stem
from yt_fetcher.writers import write_tsv
from yt_fetcher.youtube import download_media

app = FastAPI(title="YT Fetcher")

STATIC_DIR = Path(__file__).parent.parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return "<h1>Static directory not initialized</h1>"


def cleanup_dir(path: Path):
    shutil.rmtree(path, ignore_errors=True)


@app.post("/api/download")
async def download_endpoint(
    background_tasks: BackgroundTasks,
    urls: str = Form(...),
    subtitles: bool = Form(False),
    mp3: bool = Form(False),
    mp4: bool = Form(False),
):
    url_list = [line.strip() for line in urls.splitlines() if line.strip()]
    if not url_list:
        raise HTTPException(status_code=400, detail="No URLs provided")

    if not (subtitles or mp3 or mp4):
        raise HTTPException(status_code=400, detail="Please select at least one format to download.")

    tmp_dir = Path(tempfile.mkdtemp(prefix="yt_fetcher_"))
    zip_path = tmp_dir / "downloads.zip"

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for url in url_list:
                try:
                    sub_path, mp3_path, mp4_path = download_media(url, tmp_dir, dl_sub=subtitles, dl_mp3=mp3, dl_mp4=mp4)
                    
                    if subtitles and sub_path:
                        rows = parse_subtitle_file(sub_path)
                        stem = base_stem(sub_path)
                        tsv_path = tmp_dir / f"{stem}.tsv"
                        write_tsv(rows, tsv_path)
                        zf.write(tsv_path, tsv_path.name)
                        sub_path.unlink(missing_ok=True)
                        
                    if mp3 and mp3_path:
                        zf.write(mp3_path, mp3_path.name)
                        
                    if mp4 and mp4_path:
                        zf.write(mp4_path, mp4_path.name)
                except Exception as e:
                    print(f"Error processing {url}: {e}")
        
        background_tasks.add_task(cleanup_dir, tmp_dir)
        return FileResponse(
            path=zip_path,
            filename="youtube_downloads.zip",
            media_type="application/zip"
        )
    except Exception as e:
        cleanup_dir(tmp_dir)
        raise HTTPException(status_code=500, detail=str(e))
