import csv
from pathlib import Path

from yt_fetcher.models import SubtitleRow

def write_tsv(rows: list[SubtitleRow], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["no", "start", "end", "en"])
        for i, row in enumerate(rows, start=1):
            writer.writerow([i, row.start, row.end, row.en])
