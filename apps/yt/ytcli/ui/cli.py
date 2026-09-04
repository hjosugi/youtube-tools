from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import config_path, load_config, save_config
from .download import (
    AUDIO_FORMATS,
    AUDIO_QUALITIES,
    VIDEO_FORMATS,
    VIDEO_QUALITIES,
    download,
    list_subtitles,
)
from .interactive import PromptCancelled, run_wizard
from .models import AppError
from .modes import describe_modes, parse_modes
from .options import Options, validate_sub_formats
from .utils import split_list
from .writers import SUBTITLE_FORMATS

EPILOG = f"""\
examples:
  yt URL                          subtitles in the configured default languages
  yt URL -m avs                   audio, video and subtitles in one run
  yt URL -m s -l en,ja            English and Japanese subtitles
  yt URL -m s -l all              every subtitle track the video offers
  yt URL -m v --vq 1080           video capped at 1080p
  yt URL -m a --aq 192            audio re-encoded at 192 kbps
  yt URL -m s -f srt,tsv,md       write the same subtitles in three formats
  yt --gui                        open the desktop window
  yt -o ~/Downloads --save-config remember an output directory and exit

config file: {config_path()}
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt",
        description="Download YouTube audio, video and subtitles.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("urls", nargs="*", help="one or more YouTube URLs")
    parser.add_argument(
        "-m",
        "--mode",
        metavar="AVS",
        help="what to download: any of a (audio), v (video), s (subtitle), or all. Example: -m avs",
    )
    parser.add_argument(
        "-l",
        "--lang",
        metavar="LIST",
        help="subtitle languages, comma separated, or all. Example: -l en,ja",
    )
    parser.add_argument(
        "-f",
        "--sub-format",
        metavar="LIST",
        help=f"subtitle output formats, comma separated. Choose from: {', '.join(SUBTITLE_FORMATS)}",
    )
    parser.add_argument(
        "--no-auto-subs",
        dest="auto_subs",
        action="store_false",
        default=None,
        help="only use human-written captions, skip YouTube auto-generated ones",
    )
    parser.add_argument(
        "--vq", "--video-quality", dest="video_quality", choices=VIDEO_QUALITIES,
        help="maximum video height",
    )
    parser.add_argument(
        "--video-format", dest="video_format", choices=VIDEO_FORMATS, help="video container"
    )
    parser.add_argument(
        "--aq", "--audio-quality", dest="audio_quality", choices=AUDIO_QUALITIES,
        help="audio bitrate in kbps",
    )
    parser.add_argument(
        "--audio-format", dest="audio_format", choices=AUDIO_FORMATS, help="audio codec"
    )
    parser.add_argument("-o", "--output", metavar="DIR", help="output directory")
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="ask for every option step by step"
    )
    parser.add_argument("-g", "--gui", action="store_true", help="open the desktop window")
    parser.add_argument(
        "--list-subs", action="store_true", help="show the subtitle languages a video offers and exit"
    )
    parser.add_argument(
        "--insecure", action="store_true", help="skip TLS certificate verification (last resort)"
    )
    parser.add_argument(
        "--save-config", action="store_true", help="store the current options as defaults"
    )
    parser.add_argument("--show-config", action="store_true", help="print the effective defaults and exit")
    parser.add_argument("--config-path", action="store_true", help="print the config file path and exit")
    parser.add_argument("--version", action="version", version=f"yt {__version__}")
    return parser


def apply_overrides(options: Options, args: argparse.Namespace) -> Options:
    options.urls = list(args.urls)
    if args.mode:
        options.modes = parse_modes(args.mode)
    if args.lang:
        options.sub_langs = split_list(args.lang) or options.sub_langs
    if args.sub_format:
        options.sub_formats = validate_sub_formats(split_list(args.sub_format))
    if args.auto_subs is not None:
        options.auto_subs = args.auto_subs
    for name in ("video_quality", "video_format", "audio_quality", "audio_format", "output"):
        value = getattr(args, name)
        if value:
            setattr(options, name, value)
    options.insecure = args.insecure
    return options


def main(argv: list[str] | None = None) -> int:
    try:
        return _run(build_parser().parse_args(argv))
    except AppError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


def _run(args: argparse.Namespace) -> int:

    if args.config_path:
        print(config_path())
        return 0

    options = apply_overrides(Options.from_config(load_config()), args)

    if args.show_config:
        from .config import format_config

        print(f"# {config_path()}")
        print(format_config(options.to_config()))
        return 0

    if args.save_config:
        path = save_config(options.to_config())
        print(f"Saved defaults to {path}")
        if not options.urls and not args.gui:
            return 0

    if args.gui:
        from .gui import run_gui

        return run_gui(options)

    if args.list_subs:
        return show_subtitle_languages(options)

    if args.interactive or (not options.urls and sys.stdin.isatty()):
        try:
            run_wizard(options)
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
        except PromptCancelled:
            print("Cancelled.")
            return 1

    if not options.urls:
        print("error: no URL given. Run `yt --gui`, `yt -i`, or `yt --help`.", file=sys.stderr)
        return 1

    return run_downloads(options)


def show_subtitle_languages(options: Options) -> int:
    if not options.urls:
        print("error: --list-subs needs a URL.", file=sys.stderr)
        return 1
    failures = 0
    for url in options.urls:
        try:
            tracks = list_subtitles(url, log=lambda _line: None, insecure=options.insecure)
        except AppError as error:
            print(f"error ({url}): {error}", file=sys.stderr)
            failures += 1
            continue
        print(url)
        print(f"  manual   : {', '.join(tracks['manual']) or '(none)'}")
        print(f"  automatic: {', '.join(tracks['automatic']) or '(none)'}")
    return 1 if failures else 0


def run_downloads(options: Options) -> int:
    out_dir = options.out_dir
    print(f"Modes  : {describe_modes(options.modes)}")
    print(f"Output : {out_dir}")

    failures = 0
    saved: list[str] = []
    for url in options.urls:
        print(f"\n=== {url}")
        try:
            result = download(options.to_request(url))
        except AppError as error:
            print(f"error ({url}): {error}", file=sys.stderr)
            failures += 1
            continue
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130
        except Exception as error:  # yt-dlp and ffmpeg raise a wide range of errors
            print(f"unexpected error ({url}): {error}", file=sys.stderr)
            failures += 1
            continue
        saved.extend(path.name for path in result.files)
        for warning in result.warnings:
            print(f"note: {warning}")

    print(f"\nDone. {len(saved)} file(s) in {out_dir}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
