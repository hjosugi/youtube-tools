"""Finding ffmpeg, and fetching our own copy, without touching the network."""

import hashlib
import os
import zipfile
from pathlib import Path

import pytest

from ytcli import ffmpeg
from ytcli.models import AppError

# Taken before the autouse fixture swaps it for a function that refuses to download.
real_fetch = ffmpeg.fetch

BINARY = b"#!/bin/sh\necho fake ffmpeg\n"


@pytest.fixture
def no_system_ffmpeg(monkeypatch):
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda _name: None)


@pytest.fixture
def wheel(tmp_path) -> Path:
    """A stand-in for the imageio-ffmpeg wheel: a zip with one binary inside."""
    path = tmp_path / "wheel.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("imageio_ffmpeg/__init__.py", "")
        archive.writestr("imageio_ffmpeg/binaries/ffmpeg-test-v1", BINARY)
    return path


@pytest.fixture
def fake_fetch(monkeypatch, wheel):
    """Serve the stand-in wheel instead of PyPI, counting how often it is asked for."""
    calls: list[str] = []

    def fetch(url, archive, digest, progress):
        calls.append(url)
        archive.write_bytes(wheel.read_bytes())
        if progress is not None:
            progress(wheel.stat().st_size, wheel.stat().st_size)

    monkeypatch.setattr(ffmpeg, "fetch", fetch)
    return calls


def test_a_system_ffmpeg_wins(monkeypatch):
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda _name: "/usr/bin/ffmpeg")
    assert ffmpeg.status() == "system"
    assert ffmpeg.ensure() is None  # None tells yt-dlp to use PATH, ffprobe included


def test_downloads_once_and_reuses_the_copy(no_system_ffmpeg, fake_fetch):
    lines: list[str] = []
    assert ffmpeg.status() == "downloadable"

    location = ffmpeg.ensure(lines.append)

    assert Path(location) == ffmpeg.cached_path()
    assert Path(location).read_bytes() == BINARY
    assert os.access(location, os.X_OK)
    assert any("first time only" in line for line in lines)
    assert ffmpeg.status() == "cached"

    assert ffmpeg.ensure() == location
    assert len(fake_fetch) == 1


def test_the_download_reports_progress(no_system_ffmpeg, fake_fetch):
    seen: list[tuple[int, int]] = []
    ffmpeg.ensure(progress=lambda done, total: seen.append((done, total)))
    assert seen and seen[-1][0] == seen[-1][1]


def test_the_wheel_matches_this_platform(no_system_ffmpeg, fake_fetch):
    ffmpeg.ensure()
    tag, _digest = ffmpeg.WHEELS[ffmpeg.platform_key()]
    assert fake_fetch[0].endswith(f"imageio_ffmpeg-{ffmpeg.WHEEL_VERSION}-py3-none-{tag}.whl")


def test_nothing_is_left_behind_when_the_download_fails(no_system_ffmpeg, monkeypatch):
    def broken(url, archive, digest, progress):
        archive.write_bytes(b"half")
        raise OSError("connection reset")

    monkeypatch.setattr(ffmpeg, "fetch", broken)
    with pytest.raises(AppError, match="Could not download ffmpeg: connection reset"):
        ffmpeg.ensure()
    assert not ffmpeg.cached_path().exists()
    assert list(ffmpeg.cached_path().parent.iterdir()) == []


def test_a_platform_without_a_build_says_what_to_do(no_system_ffmpeg, monkeypatch):
    monkeypatch.setattr(ffmpeg, "platform_key", lambda: ("plan9", "mips"))
    assert ffmpeg.status() == "missing"
    with pytest.raises(AppError, match="Install ffmpeg"):
        ffmpeg.ensure()


def test_fetch_checks_the_pinned_digest(tmp_path, wheel):
    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
    seen: list[tuple[int, int]] = []

    real_fetch(wheel.as_uri(), tmp_path / "ok", digest, lambda done, total: seen.append((done, total)))
    assert (tmp_path / "ok").read_bytes() == wheel.read_bytes()
    assert seen[-1] == (wheel.stat().st_size, wheel.stat().st_size)

    with pytest.raises(AppError, match="checksum"):
        real_fetch(wheel.as_uri(), tmp_path / "bad", "0" * 64, None)


def test_an_archive_without_ffmpeg_is_refused(tmp_path):
    empty = tmp_path / "empty.whl"
    with zipfile.ZipFile(empty, "w") as archive:
        archive.writestr("README", "nothing here")
    with pytest.raises(AppError, match="no ffmpeg binary"):
        ffmpeg.unpack(empty, tmp_path / "ffmpeg")
    assert not (tmp_path / "ffmpeg").exists()


def test_every_platform_has_a_full_digest():
    assert {system for system, _arch in ffmpeg.WHEELS} == {"linux", "macos", "windows"}
    for tag, digest in ffmpeg.WHEELS.values():
        assert tag
        assert len(digest) == 64 and int(digest, 16) >= 0


def test_the_cache_directory_can_be_moved(monkeypatch, tmp_path):
    monkeypatch.setenv(ffmpeg.CACHE_DIR_ENV, str(tmp_path / "elsewhere"))
    assert ffmpeg.cache_dir() == tmp_path / "elsewhere"
    assert ffmpeg.cached_path().parent.parent == tmp_path / "elsewhere"


@pytest.mark.parametrize(
    ("platform", "variable", "tail"),
    [
        ("linux", "XDG_CACHE_HOME", ("yt",)),
        ("win32", "LOCALAPPDATA", ("yt", "Cache")),
    ],
)
def test_the_default_cache_follows_the_platform(monkeypatch, tmp_path, platform, variable, tail):
    monkeypatch.delenv(ffmpeg.CACHE_DIR_ENV)
    monkeypatch.setattr(ffmpeg.sys, "platform", platform)
    monkeypatch.setenv(variable, str(tmp_path))
    assert ffmpeg.cache_dir() == tmp_path.joinpath(*tail)


def test_macos_caches_under_library(monkeypatch):
    monkeypatch.delenv(ffmpeg.CACHE_DIR_ENV)
    monkeypatch.setattr(ffmpeg.sys, "platform", "darwin")
    assert ffmpeg.cache_dir().parts[-3:] == ("Library", "Caches", "yt")
