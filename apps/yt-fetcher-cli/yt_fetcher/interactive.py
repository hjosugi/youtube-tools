from __future__ import annotations

import argparse
from collections.abc import Callable


InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]

RESOLUTIONS = ("best", "1080", "720", "480", "360")


class PromptCancelled(Exception):
    pass


def apply_interactive_options(
    args: argparse.Namespace,
    input_fn: InputFn = input,
    output_fn: OutputFn = print,
) -> argparse.Namespace:
    output_fn("YouTube Fetcher interactive setup")
    output_fn("Press Enter to accept the default shown in brackets.")

    if not args.urls:
        entered = prompt_required("YouTube URL(s), separated by spaces", input_fn)
        args.urls = entered.split()

    if not (args.subtitles or args.mp3 or args.mp4):
        output_fn("")
        output_fn("What do you want to download?")
        args.subtitles = prompt_yes_no("Subtitles as TSV", default=True, input_fn=input_fn)
        args.mp3 = prompt_yes_no("MP3 audio", default=False, input_fn=input_fn)
        args.mp4 = prompt_yes_no("MP4 video", default=False, input_fn=input_fn)
        if not (args.subtitles or args.mp3 or args.mp4):
            output_fn("No format selected. Defaulting to subtitles.")
            args.subtitles = True

    if args.mp4:
        args.resolution = prompt_choice(
            "MP4 max resolution",
            choices=RESOLUTIONS,
            default=args.resolution,
            input_fn=input_fn,
        )

    args.output = prompt_text("Output directory", default=args.output, input_fn=input_fn)

    output_fn("")
    output_fn("Summary")
    output_fn(f"- URLs: {', '.join(args.urls)}")
    output_fn(f"- subtitles: {yes_no(args.subtitles)}")
    output_fn(f"- mp3: {yes_no(args.mp3)}")
    output_fn(f"- mp4: {yes_no(args.mp4)}")
    if args.mp4:
        output_fn(f"- resolution: {args.resolution}")
    output_fn(f"- output: {args.output}")

    if not prompt_yes_no("Start download", default=True, input_fn=input_fn):
        raise PromptCancelled("cancelled")

    return args


def prompt_required(label: str, input_fn: InputFn) -> str:
    while True:
        value = input_fn(f"{label}: ").strip()
        if value:
            return value
        print("Please enter a value.")


def prompt_text(label: str, default: str, input_fn: InputFn) -> str:
    value = input_fn(f"{label} [{default}]: ").strip()
    return value if value else default


def prompt_yes_no(label: str, default: bool, input_fn: InputFn) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        value = input_fn(f"{label} [{suffix}]: ").strip().lower()
        if not value:
            return default
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        print("Please answer y or n.")


def prompt_choice(label: str, choices: tuple[str, ...], default: str, input_fn: InputFn) -> str:
    choices_text = "/".join(choices)
    while True:
        value = input_fn(f"{label} ({choices_text}) [{default}]: ").strip()
        if not value:
            return default
        if value in choices:
            return value
        print(f"Please choose one of: {choices_text}")


def yes_no(value: bool) -> str:
    return "yes" if value else "no"

