from __future__ import annotations

import argparse

from .. import __version__
from ..models import AUDIO_FORMATS, AUDIO_QUALITIES, VIDEO_FORMATS, VIDEO_QUALITIES
from ..modes import MODE_ALIASES, parse_modes
from ..settings import Options, config_path, validate_sub_formats
from ..subtitles import SUBTITLE_FORMATS
from ..utils import split_list

# Options that are simply copied across when the flag was given.
PASS_THROUGH = ("video_quality", "video_format", "audio_quality", "audio_format", "output")

# Plain words accepted next to the URLs, so nobody has to remember `-m a` or `--gui`:
# `yt mp3 URL`, `yt mp4 sub URL`, `yt ui`.
MODE_WORDS = frozenset(MODE_ALIASES) | {"all"}
UI_WORDS = frozenset({"ui", "gui"})


def epilog() -> str:
    """Built on demand so the shown config path follows $YT_CONFIG_FILE."""
    return f"""\
examples:
  yt                              open the local web UI: paste a URL, click a button
  yt mp3 URL                      audio as MP3
  yt mp4 URL                      video as MP4
  yt sub URL                      subtitles in the configured default languages
  yt all URL                      audio, video and subtitles in one run
  yt sub URL -l en,ja             English and Japanese subtitles
  yt sub URL -l all               every subtitle track the video offers
  yt mp4 URL --vq 1080            video capped at 1080p
  yt mp3 URL --aq 192             audio re-encoded at 192 kbps
  yt sub URL -f srt,tsv,md        write the same subtitles in three formats
  yt -o ~/Downloads --save-config remember an output directory and exit

config file: {config_path()}
"""


def build_parser() -> argparse.ArgumentParser:
    """Every flag `yt` accepts."""
    parser = argparse.ArgumentParser(
        prog="yt",
        description="Download YouTube audio, video and subtitles.",
        epilog=epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "urls",
        nargs="*",
        metavar="WORD|URL",
        help="YouTube URLs, optionally with what to get: mp3, mp4, sub, all. `ui` opens the web UI",
    )
    parser.add_argument(
        "-m",
        "--mode",
        metavar="AVS",
        help="same as the words: any of a (audio), v (video), s (subtitle), or all. Example: -m avs",
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
        "--vq",
        "--video-quality",
        dest="video_quality",
        choices=VIDEO_QUALITIES,
        help="maximum video height",
    )
    parser.add_argument("--video-format", dest="video_format", choices=VIDEO_FORMATS, help="video container")
    parser.add_argument(
        "--aq",
        "--audio-quality",
        dest="audio_quality",
        choices=AUDIO_QUALITIES,
        help="audio bitrate in kbps",
    )
    parser.add_argument("--audio-format", dest="audio_format", choices=AUDIO_FORMATS, help="audio codec")
    parser.add_argument("-o", "--output", metavar="DIR", help="output directory")
    parser.add_argument("-i", "--interactive", action="store_true", help="ask for every option step by step")
    parser.add_argument(
        "-g", "--gui", "--ui", dest="gui", action="store_true", help="open the local web UI (same as `yt ui`)"
    )
    parser.add_argument("--port", type=int, metavar="N", help="port for the web UI (default: pick one)")
    parser.add_argument(
        "--no-open", action="store_true", help="start the web UI without opening a browser tab"
    )
    parser.add_argument(
        "--list-subs",
        action="store_true",
        help="show the subtitle languages a video offers and exit",
    )
    parser.add_argument(
        "--insecure", action="store_true", help="skip TLS certificate verification (last resort)"
    )
    parser.add_argument("--save-config", action="store_true", help="store the current options as defaults")
    parser.add_argument("--show-config", action="store_true", help="print the effective defaults and exit")
    parser.add_argument("--config-path", action="store_true", help="print the config file path and exit")
    parser.add_argument("--version", action="version", version=f"yt {__version__}")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command line, then fold the plain words into the flags they stand for."""
    # Intermixed, so words, URLs and flags may come in any order: `yt mp3 --aq 192 URL`.
    return absorb_words(build_parser().parse_intermixed_args(argv))


def absorb_words(args: argparse.Namespace) -> argparse.Namespace:
    """Turn `yt mp3 sub URL` into `yt URL -m mp3,sub`, and `yt ui` into `yt --gui`."""
    words = [token.lower() for token in args.urls if token.lower() in MODE_WORDS | UI_WORDS]
    args.urls = [token for token in args.urls if token.lower() not in MODE_WORDS | UI_WORDS]
    modes = [word for word in words if word in MODE_WORDS]
    if modes:
        args.mode = ",".join(([args.mode] if args.mode else []) + modes)
    if any(word in UI_WORDS for word in words):
        args.gui = True
    return args


def apply_overrides(options: Options, args: argparse.Namespace) -> Options:
    """Let the flags that were actually given win over the saved defaults."""
    options.urls = list(args.urls)
    if args.mode:
        options.modes = parse_modes(args.mode)
    if args.lang:
        options.sub_langs = split_list(args.lang) or options.sub_langs
    if args.sub_format:
        options.sub_formats = validate_sub_formats(split_list(args.sub_format))
    if args.auto_subs is not None:
        options.auto_subs = args.auto_subs
    for name in PASS_THROUGH:
        value = getattr(args, name)
        if value:
            setattr(options, name, value)
    options.insecure = args.insecure
    return options
