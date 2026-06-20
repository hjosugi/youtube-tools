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
    resolution: str = Form("best"),
):
    url_list = [line.strip() for line in urls.splitlines() if line.strip()]
    if not url_list:
        raise HTTPException(status_code=400, detail="No URLs provided")

    if not (subtitles or mp3 or mp4):
        raise HTTPException(status_code=400, detail="Please select at least one format to download.")

    tmp_dir = Path(tempfile.mkdtemp(prefix="yt_fetcher_"))
    zip_path = tmp_dir / "downloads.zip"

    try:
        generated_files = []
        errors = []
        for url in url_list:
            try:
                sub_path, mp3_path, mp4_path = download_media(url, tmp_dir, dl_sub=subtitles, dl_mp3=mp3, dl_mp4=mp4, resolution=resolution)
                
                if subtitles and sub_path:
                    rows = parse_subtitle_file(sub_path)
                    stem = base_stem(sub_path)
                    tsv_path = tmp_dir / f"{stem}.tsv"
                    write_tsv(rows, tsv_path)
                    generated_files.append(tsv_path)
                    sub_path.unlink(missing_ok=True)
                    
                if mp3 and mp3_path:
                    new_mp3 = tmp_dir / f"{base_stem(mp3_path)}{mp3_path.suffix}"
                    if not new_mp3.exists():
                        mp3_path.rename(new_mp3)
                        generated_files.append(new_mp3)
                    else:
                        generated_files.append(mp3_path)
                    
                if mp4 and mp4_path:
                    new_mp4 = tmp_dir / f"{base_stem(mp4_path)}{mp4_path.suffix}"
                    if not new_mp4.exists():
                        mp4_path.rename(new_mp4)
                        generated_files.append(new_mp4)
                    else:
                        generated_files.append(mp4_path)
            except Exception as e:
                print(f"Error processing {url}: {e}")
                errors.append(str(e))
        
        background_tasks.add_task(cleanup_dir, tmp_dir)
        
        if not generated_files:
            error_details = " | ".join(errors) if errors else "No English subtitles found or matches condition."
            raise HTTPException(status_code=500, detail=f"Failed to fetch any files. Reason: {error_details}")
            
        if len(generated_files) == 1:
            single_file = generated_files[0]
            return FileResponse(
                path=single_file,
                filename=single_file.name
            )

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in generated_files:
                zf.write(f, f.name)
                
        return FileResponse(
            path=zip_path,
            filename="youtube_downloads.zip",
            media_type="application/zip"
        )
    except Exception as e:
        cleanup_dir(tmp_dir)
        raise HTTPException(status_code=500, detail=str(e))
