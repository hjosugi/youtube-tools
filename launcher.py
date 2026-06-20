from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Tool:
    key: str
    label: str
    cwd: Path
    command: list[str]


def python_command(script: str, *args: str) -> list[str]:
    if shutil.which("uv"):
        return ["uv", "run", "python", script, *args]
    return [sys.executable, script, *args]


def streamlit_command(script: str) -> list[str]:
    if shutil.which("streamlit"):
        return ["streamlit", "run", script]
    return [sys.executable, "-m", "streamlit", "run", script]


TOOLS = [
    Tool(
        key="1",
        label="Bilingual subtitle generator",
        cwd=ROOT / "apps" / "bilingual-subtitle",
        command=python_command("main.py", "--interactive"),
    ),
    Tool(
        key="2",
        label="YT Fetcher CLI",
        cwd=ROOT / "apps" / "yt-fetcher-cli",
        command=python_command("cli.py", "--interactive"),
    ),
    Tool(
        key="3",
        label="YT Fetcher web app",
        cwd=ROOT / "apps" / "yt-fetcher-web",
        command=python_command("main.py"),
    ),
    Tool(
        key="4",
        label="Simple Streamlit downloader",
        cwd=ROOT / "apps" / "simple-youtube-downloader",
        command=streamlit_command("src/main.py"),
    ),
]


def choose_tool() -> Tool:
    print("YouTube Tools")
    print("Choose what you want to use:")
    for tool in TOOLS:
        print(f"{tool.key}. {tool.label}")
    while True:
        choice = input("Tool [1]: ").strip() or "1"
        for tool in TOOLS:
            if tool.key == choice:
                return tool
        print("Please choose one of: 1, 2, 3, 4")


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive launcher for YouTube tools")
    parser.add_argument("--list", action="store_true", help="List available tools")
    parser.add_argument("--dry-run", choices=[tool.key for tool in TOOLS], help="Print the command without running it")
    args = parser.parse_args()

    if args.list:
        for tool in TOOLS:
            print(f"{tool.key}: {tool.label}")
        return 0

    tool = next((item for item in TOOLS if item.key == args.dry_run), None) if args.dry_run else choose_tool()
    if tool is None:
        return 1

    if args.dry_run:
        print(f"cd {tool.cwd}")
        print(" ".join(tool.command))
        return 0

    print(f"Starting: {tool.label}")
    return subprocess.run(tool.command, cwd=tool.cwd).returncode


if __name__ == "__main__":
    raise SystemExit(main())

