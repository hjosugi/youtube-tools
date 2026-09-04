"""Build the standalone `yt` binary for the platform this script runs on.

    uv run python build.py            # -> dist/yt-<os>-<arch>[.exe]
    uv run python build.py --keep     # keep the plain dist/yt name as well
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"

SYSTEMS = {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}
ARCHITECTURES = {"x86_64": "x86_64", "amd64": "x86_64", "arm64": "arm64", "aarch64": "arm64"}


def asset_name() -> str:
    system = SYSTEMS.get(platform.system(), platform.system().lower())
    machine = platform.machine().lower()
    architecture = ARCHITECTURES.get(machine, machine or "unknown")
    suffix = ".exe" if system == "windows" else ""
    return f"yt-{system}-{architecture}{suffix}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--keep", action="store_true", help="also keep the unsuffixed dist/yt binary")
    args = parser.parse_args()

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--clean",
        "--noconfirm",
        "--name",
        "yt",
        # yt-dlp resolves its extractors at runtime, so PyInstaller cannot see them.
        "--collect-submodules",
        "yt_dlp",
        # The GUI needs Tcl/Tk shipped inside the binary.
        "--hidden-import",
        "tkinter",
        str(ROOT / "yt.py"),
    ]
    print(" ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        return result.returncode

    built = DIST / ("yt.exe" if platform.system() == "Windows" else "yt")
    if not built.is_file():
        print(f"error: PyInstaller did not produce {built}", file=sys.stderr)
        return 1

    target = DIST / asset_name()
    if target != built:
        shutil.copy2(built, target) if args.keep else shutil.move(str(built), str(target))
        target.chmod(0o755)
    print(f"\nBuilt {target} ({target.stat().st_size / 1_048_576:.1f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
