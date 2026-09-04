"""A stand-in for yt-dlp so the download flow can be tested without the network."""

from pathlib import Path

import pytest

from ytcli.download import stages
from ytcli.models import AppError, SubtitleTracks


class FakeYtDlp:
    """Records every pass and writes the files a real run would have produced."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.tracks: SubtitleTracks | None = SubtitleTracks(("en",), ("en", "de"))
        self.produce: dict[str, list[tuple[str, str]]] = {}
        self.fail: set[str] = set()

    @property
    def stages_run(self) -> list[str]:
        return [name for name, _ in self.calls]

    def options_for(self, stage: str) -> dict:
        return next(options for name, options in self.calls if name == stage)

    def run(self, ydl_options: dict, url: str) -> None:
        work_dir = Path(ydl_options["outtmpl"]).parent
        self.calls.append((work_dir.name, ydl_options))
        if work_dir.name in self.fail:
            raise RuntimeError(f"{work_dir.name} boom")
        for filename, content in self.produce.get(work_dir.name, []):
            (work_dir / filename).write_text(content, encoding="utf-8")

    def list_subtitles(self, url: str, log=None, insecure: bool = False) -> SubtitleTracks:
        if self.tracks is None:
            raise AppError("Could not read video info: boom")
        return self.tracks


@pytest.fixture
def fake(monkeypatch) -> FakeYtDlp:
    """Patch the two functions that reach the network."""
    instance = FakeYtDlp()
    monkeypatch.setattr(stages, "run_download", instance.run)
    monkeypatch.setattr(stages, "list_subtitles", instance.list_subtitles)
    return instance
