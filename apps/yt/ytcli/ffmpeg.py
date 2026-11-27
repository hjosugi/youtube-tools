"""Find ffmpeg, or fetch a private copy the first time audio or video needs it.

MP3 extraction and MP4 merging both need ffmpeg, and asking people to install it first is
the biggest hurdle of the whole tool. A system ffmpeg always wins. Without one we download
the static build that the `imageio-ffmpeg` project publishes on PyPI, check it against a
pinned SHA-256 and keep it in the cache directory, so it is fetched once per machine.
"""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import ssl
import sys
import threading
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

from .models import AppError

Logger = Callable[[str], None]
Progress = Callable[[int, int], None]

# Bump the version and every digest together; Dependabot cannot see this pin.
# Digests: https://pypi.org/pypi/imageio-ffmpeg/<version>/json
WHEEL_VERSION = "0.8.2"
WHEEL_URL = (
    "https://files.pythonhosted.org/packages/py3/i/imageio-ffmpeg/imageio_ffmpeg-{version}-py3-none-{tag}.whl"
)
WHEELS: dict[tuple[str, str], tuple[str, str]] = {
    ("linux", "x86_64"): (
        "manylinux_2_28_x86_64",
        "4749aa8d7c46c0c194373e97d0dba0b8cee66cd1c4fcea84a91ac37d46f79dc1",
    ),
    ("linux", "arm64"): (
        "manylinux_2_28_aarch64",
        "adc2265a001ea60b92b11898c01e47a4d1f3ff8443d7d5992c8e907dbfe8da92",
    ),
    ("macos", "x86_64"): (
        "macosx_10_13_x86_64",
        "f9cbd6416cf0238f0e94167d91b3326b22d4588eeae1fd788c2e7cac9fc0c7c5",
    ),
    ("macos", "arm64"): (
        "macosx_12_0_arm64",
        "113f7c0b6ea4bbc67005ddb0d8b63ed27a35b01c13c79ea9c459442f627aa4f3",
    ),
    ("windows", "x86_64"): (
        "win_amd64",
        "c5d528e1daa9c17c71d7a600c31e1a0983ca739a20dd014159b2b7431b0b1ea7",
    ),
    ("windows", "arm64"): (
        "win_arm64",
        "bfff5584740caa1e84375f53d3e7dc2dd12051d5c56e3bc3611c76c6e2300c76",
    ),
}

SYSTEMS = {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}
ARCHITECTURES = {"x86_64": "x86_64", "amd64": "x86_64", "arm64": "arm64", "aarch64": "arm64"}
CACHE_DIR_ENV = "YT_CACHE_DIR"
CHUNK = 1 << 16

_download_lock = threading.Lock()


def platform_key() -> tuple[str, str]:
    """This machine as (system, architecture), in the spelling the release assets use."""
    system = SYSTEMS.get(platform.system(), platform.system().lower())
    machine = platform.machine().lower()
    return system, ARCHITECTURES.get(machine, machine or "unknown")


def cache_dir() -> Path:
    """Where downloaded helpers live: $YT_CACHE_DIR, else the platform cache directory."""
    override = os.environ.get(CACHE_DIR_ENV)
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "yt" / "Cache"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "yt"
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "yt"


def cached_path() -> Path:
    """Where our own copy of ffmpeg is kept once it has been downloaded."""
    name = "ffmpeg.exe" if platform_key()[0] == "windows" else "ffmpeg"
    return cache_dir() / f"ffmpeg-{WHEEL_VERSION}" / name


def status() -> str:
    """'system', 'cached', 'downloadable' or 'missing', for the UI and `yt --doctor`."""
    if shutil.which("ffmpeg"):
        return "system"
    if cached_path().is_file():
        return "cached"
    return "downloadable" if platform_key() in WHEELS else "missing"


def ensure(log: Logger | None = None, progress: Progress | None = None) -> str | None:
    """Make ffmpeg available and return the value for yt-dlp's ffmpeg_location.

    None means "the one on PATH", which also lets yt-dlp find ffprobe next to it.
    """
    if shutil.which("ffmpeg"):
        return None
    target = cached_path()
    with _download_lock:  # two jobs starting together must not download twice
        if not target.is_file():
            download(target, log or _silent, progress)
    return str(target)


def download(target: Path, log: Logger, progress: Progress | None = None) -> None:
    """Fetch the pinned wheel, verify it and unpack the one binary inside."""
    wheel = WHEELS.get(platform_key())
    if wheel is None:
        raise AppError(
            "ffmpeg is not installed and there is no automatic download for "
            f"{'-'.join(platform_key())}. Install ffmpeg and put it on PATH."
        )
    tag, digest = wheel
    url = WHEEL_URL.format(version=WHEEL_VERSION, tag=tag)
    target.parent.mkdir(parents=True, exist_ok=True)
    archive = target.with_name(target.name + ".download")
    log("ffmpeg is not installed: downloading a private copy (first time only)...")
    try:
        fetch(url, archive, digest, progress)
        unpack(archive, target)
    except OSError as error:
        raise AppError(f"Could not download ffmpeg: {error}") from error
    finally:
        archive.unlink(missing_ok=True)
    log(f"ffmpeg ready: {target}")


def fetch(url: str, archive: Path, digest: str, progress: Progress | None) -> None:
    """Stream the wheel to disk, failing when its SHA-256 is not the pinned one."""
    sha = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=60, context=_tls_context()) as response:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with archive.open("wb") as handle:
            while chunk := response.read(CHUNK):
                handle.write(chunk)
                sha.update(chunk)
                done += len(chunk)
                if progress is not None:
                    progress(done, total)
    if sha.hexdigest() != digest:
        raise AppError("Could not download ffmpeg: the file did not match its checksum.")


def unpack(archive: Path, target: Path) -> None:
    """Pull the single ffmpeg executable out of the wheel and make it runnable."""
    with zipfile.ZipFile(archive) as wheel:
        members = [name for name in wheel.namelist() if "/binaries/ffmpeg" in name]
        if not members:
            raise AppError("Could not download ffmpeg: the archive holds no ffmpeg binary.")
        partial = target.with_name(target.name + ".partial")
        with wheel.open(members[0]) as source, partial.open("wb") as handle:
            shutil.copyfileobj(source, handle)
    partial.chmod(0o755)
    partial.replace(target)  # atomic, so a half-written file is never mistaken for ffmpeg


def _tls_context() -> ssl.SSLContext:
    """Frozen builds have no system CA store, so prefer certifi's bundle."""
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _silent(_line: str) -> None:
    """Default logger for callers that only want the path."""
