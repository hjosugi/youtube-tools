from __future__ import annotations

import argparse

from .. import __version__
from ..models import AUDIO_FORMATS, AUDIO_QUALITIES, VIDEO_FORMATS, VIDEO_QUALITIES
from ..modes import parse_modes
from ..settings import Options, config_path, validate_sub_formats
from ..subtitles import SUBTITLE_FORMATS
from ..utils import split_list

# Options that are simply copied across when the flag was given.
PASS_THROUGH = ("video_quality", "video_format", "audio_quality", "audio_format", "output")


def epilog() -> str:
    """Built on demand so the shown config path follows $YT_CONFIG_FILE."""
    return f"""\
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
    """Every flag `yt` accepts."""
    parser = argparse.ArgumentParser(
        prog="yt",
        description="Download YouTube audio, video and subtitles.",
        epilog=epilog(),
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
    parser.add_argument("-g", "--gui", action="store_true", help="open the desktop window")
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
