from __future__ import annotations

from collections.abc import Callable

from .download import AUDIO_FORMATS, AUDIO_QUALITIES, VIDEO_FORMATS, VIDEO_QUALITIES
from .models import AppError
from .modes import describe_modes, parse_modes
from .utils import split_list
from .writers import SUBTITLE_FORMATS

InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]


class PromptCancelled(Exception):
    pass


def run_wizard(options, input_fn: InputFn = input, output_fn: OutputFn = print):
    """Fill in missing options by asking. Mutates and returns the options object."""
    output_fn("yt interactive setup")
    output_fn("Press Enter to accept the value in brackets.")
    output_fn("")

    if not options.urls:
        options.urls = prompt_required("YouTube URL(s), separated by spaces", input_fn).split()

    options.modes = prompt_loop(
        "Modes: a=audio v=video s=subtitle",
        default=options.modes,
        parse=parse_modes,
        input_fn=input_fn,
        output_fn=output_fn,
    )

    if "s" in options.modes:
        options.sub_langs = prompt_list(
            "Subtitle languages (comma separated, or all)",
            default=options.sub_langs,
            input_fn=input_fn,
        )
        options.sub_formats = prompt_subset(
            "Subtitle formats",
            default=options.sub_formats,
            allowed=SUBTITLE_FORMATS,
            input_fn=input_fn,
            output_fn=output_fn,
        )

    if "v" in options.modes:
        options.video_quality = prompt_choice(
            "Video quality", VIDEO_QUALITIES, options.video_quality, input_fn, output_fn
        )
        options.video_format = prompt_choice(
            "Video container", VIDEO_FORMATS, options.video_format, input_fn, output_fn
        )

    if "a" in options.modes:
        options.audio_quality = prompt_choice(
            "Audio quality (kbps)", AUDIO_QUALITIES, options.audio_quality, input_fn, output_fn
        )
        options.audio_format = prompt_choice(
            "Audio format", AUDIO_FORMATS, options.audio_format, input_fn, output_fn
        )

    options.output = prompt_text("Output directory", options.output, input_fn)

    output_fn("")
    output_fn("Summary")
    output_fn(f"- urls    : {', '.join(options.urls)}")
    output_fn(f"- modes   : {describe_modes(options.modes)}")
    if "s" in options.modes:
        output_fn(f"- subs    : {','.join(options.sub_langs)} as {','.join(options.sub_formats)}")
    if "v" in options.modes:
        output_fn(f"- video   : {options.video_format} @ {options.video_quality}")
    if "a" in options.modes:
        output_fn(f"- audio   : {options.audio_format} @ {options.audio_quality}")
    output_fn(f"- output  : {options.output}")

    if not prompt_yes_no("Start download", True, input_fn, output_fn):
        raise PromptCancelled("cancelled")
    return options


def prompt_required(label: str, input_fn: InputFn) -> str:
    while True:
        value = input_fn(f"{label}: ").strip()
        if value:
            return value


def prompt_text(label: str, default: str, input_fn: InputFn) -> str:
    return input_fn(f"{label} [{default}]: ").strip() or default


def prompt_loop(label: str, default: str, parse, input_fn: InputFn, output_fn: OutputFn) -> str:
    while True:
        raw = input_fn(f"{label} [{default}]: ").strip() or default
        try:
            return parse(raw)
        except AppError as error:
            output_fn(str(error))


def prompt_list(label: str, default: tuple[str, ...], input_fn: InputFn) -> tuple[str, ...]:
    raw = input_fn(f"{label} [{','.join(default)}]: ").strip()
    return split_list(raw) if raw else default


def prompt_subset(
    label: str,
    default: tuple[str, ...],
    allowed: tuple[str, ...],
    input_fn: InputFn,
    output_fn: OutputFn,
) -> tuple[str, ...]:
    while True:
        raw = input_fn(f"{label} ({'/'.join(allowed)}) [{','.join(default)}]: ").strip()
        if not raw:
            return default
        chosen = split_list(raw)
        unknown = [item for item in chosen if item not in allowed]
        if unknown:
            output_fn(f"Unknown format(s): {', '.join(unknown)}")
            continue
        return chosen


def prompt_choice(
    label: str,
    choices: tuple[str, ...],
    default: str,
    input_fn: InputFn,
    output_fn: OutputFn,
) -> str:
    while True:
        value = input_fn(f"{label} ({'/'.join(choices)}) [{default}]: ").strip()
        if not value:
            return default
        if value in choices:
            return value
        output_fn(f"Please choose one of: {'/'.join(choices)}")


def prompt_yes_no(label: str, default: bool, input_fn: InputFn, output_fn: OutputFn) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        value = input_fn(f"{label} [{suffix}]: ").strip().lower()
        if not value:
            return default
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        output_fn("Please answer y or n.")
