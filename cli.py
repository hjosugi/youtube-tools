import argparse
import sys
from pathlib import Path
import tempfile
import shutil

from yt_fetcher.youtube import download_media
from yt_fetcher.parsers import parse_subtitle_file
from yt_fetcher.writers import write_tsv
from yt_fetcher.utils import base_stem
from yt_fetcher.models import AppError

def main():
    parser = argparse.ArgumentParser(description="yt-fetch-cli: Download YouTube Subtitles, MP3, and MP4")
    parser.add_argument("urls", nargs='+', help="YouTube URLs to download")
    parser.add_argument("--subtitles", action="store_true", help="Download English subtitles (converted to TSV)")
    parser.add_argument("--mp3", action="store_true", help="Download MP3 audio")
    parser.add_argument("--mp4", action="store_true", help="Download MP4 video")
    parser.add_argument("--resolution", default="best", choices=["best", "1080", "720", "480", "360"], help="MP4 resolution")
    parser.add_argument("-o", "--output", default=".", help="Output directory (default: current directory)")

    args = parser.parse_args()

    if not (args.subtitles or args.mp3 or args.mp4):
        print("Error: You must specify at least one of --subtitles, --mp3, or --mp4.")
        sys.exit(1)

    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td)
        for url in args.urls:
            print(f"Processing: {url}")
            try:
                sub_path, mp3_path, mp4_path = download_media(
                    url=url,
                    out_dir=tmp_dir,
                    dl_sub=args.subtitles,
                    dl_mp3=args.mp3,
                    dl_mp4=args.mp4,
                    resolution=args.resolution
                )

                if args.subtitles and sub_path:
                    print("Converting subtitles to TSV...")
                    rows = parse_subtitle_file(sub_path)
                    stem = base_stem(sub_path)
                    tsv_path = out_dir / f"{stem}.tsv"
                    write_tsv(rows, tsv_path)
                    print(f"Saved: {tsv_path}")
                
                if args.mp3 and mp3_path:
                    final_mp3 = out_dir / f"{base_stem(mp3_path)}{mp3_path.suffix}"
                    shutil.move(str(mp3_path), str(final_mp3))
                    print(f"Saved: {final_mp3}")
                
                if args.mp4 and mp4_path:
                    final_mp4 = out_dir / f"{base_stem(mp4_path)}{mp4_path.suffix}"
                    shutil.move(str(mp4_path), str(final_mp4))
                    print(f"Saved: {final_mp4}")
                    
            except AppError as e:
                print(f"Error ({url}): {e}", file=sys.stderr)
            except Exception as e:
                print(f"Unexpected error ({url}): {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
