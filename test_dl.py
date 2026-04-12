import tempfile
from pathlib import Path
import traceback

from yt_fetcher.youtube import download_media
from yt_fetcher.parsers import parse_subtitle_file

url = "https://www.youtube.com/watch?v=CpxQDfGReak&t=11136s"

try:
    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td)
        sub, mp3, mp4 = download_media(url, tmp_dir, True, False, False)
        print("Downloaded:", sub)
        if sub:
            rows = parse_subtitle_file(sub)
            print("Parsed rows:", len(rows))
except Exception as e:
    print("ERROR OCCURRED:")
    traceback.print_exc()

