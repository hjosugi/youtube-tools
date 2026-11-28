from __future__ import annotations

import argparse
import sys
from importlib.resources import files

from ..download import download_all, list_subtitles
from ..models import AppError
from ..modes import describe_modes
from ..settings import Options, config_path, format_config, save_config
from . import prompts
from .args import COMPLETION_FILES, apply_overrides, parse_args
from .wizard import PromptCancelled, run_wizard


def print_error(line: str) -> None:
    """Everything the user should see on stderr goes through here."""
    print(line, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """Run one `yt` invocation and return its exit code."""
    try:
        return run(parse_args(argv))
    except AppError as error:
        print_error(f"error: {error}")
        return 1
    except KeyboardInterrupt:
        print_error("\nInterrupted.")
        return 130


def run(args: argparse.Namespace) -> int:
    """Dispatch to whichever mode the flags asked for."""
    if args.completion:
        script = files("ytcli").joinpath("completions", COMPLETION_FILES[args.completion])
        sys.stdout.write(script.read_text(encoding="utf-8"))
        return 0
    if args.config_path:
        print(config_path())
        return 0

    options = apply_overrides(Options.load(), args)

    if args.show_config:
        print(f"# {config_path()}")
        print(format_config(options.to_config()))
        return 0

    if args.save_config:
        print(f"Saved defaults to {save_config(options.to_config())}")
        if not options.urls and not args.gui:
            return 0

    if args.list_subs:
        return show_subtitle_languages(options)

    # A bare `yt` (or a double-click on the binary) opens the UI: nothing to remember.
    if args.gui or not (options.urls or args.interactive or args.mode):
        return open_ui(options, args)

    try:
        if args.interactive:
            run_wizard(options)
        elif not options.urls and sys.stdin.isatty():
            # `yt mp3` already said what to get, so the URL is the only thing left to ask.
            options.urls = prompts.url_list("YouTube URL(s)", input)
    except (EOFError, KeyboardInterrupt):
        print()
        return 1
    except PromptCancelled:
        print("Cancelled.")
        return 1

    if not options.urls:
        print_error("error: no URL given. Try `yt mp3 URL`, or run `yt` alone to open the UI.")
        return 1

    return run_downloads(options)


def open_ui(options: Options, args: argparse.Namespace) -> int:
    """Start the local web UI. Imported late so plain downloads never load the server."""
    from .web import run_ui

    # Started from a terminal, the server lives until Ctrl+C. Started by a double-click
    # there is nothing to press, so it leaves a few minutes after the last tab is closed.
    linger = None if sys.stdin.isatty() else 180.0
    return run_ui(options, port=args.port, open_browser=not args.no_open, linger=linger)


def show_subtitle_languages(options: Options) -> int:
    """Print the manual and automatic subtitle languages of every given URL."""
    if not options.urls:
        print_error("error: --list-subs needs a URL.")
        return 1
    failures = 0
    for url in options.urls:
        try:
            tracks = list_subtitles(url, insecure=options.insecure)
        except AppError as error:
            print_error(f"error ({url}): {error}")
            failures += 1
            continue
        print(url)
        print(f"  manual   : {', '.join(tracks.manual) or '(none)'}")
        print(f"  automatic: {', '.join(tracks.automatic) or '(none)'}")
    return 1 if failures else 0


def run_downloads(options: Options) -> int:
    """Download every URL in turn, reporting failures without stopping the run."""
    print(f"Modes  : {describe_modes(options.modes)}")
    print(f"Output : {options.out_dir}")

    report = download_all(options, report_error=print_error)
    print(f"\nDone. {report.saved} file(s) in {options.out_dir}")
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
