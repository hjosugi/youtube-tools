from __future__ import annotations

from ..models import AUDIO_FORMATS, AUDIO_QUALITIES, VIDEO_FORMATS, VIDEO_QUALITIES
from ..modes import describe_modes, parse_modes
from ..settings import Options
from ..subtitles import SUBTITLE_FORMATS
from . import prompts
from .prompts import InputFn, OutputFn, PromptCancelled

__all__ = ["PromptCancelled", "run_wizard"]


def run_wizard(
    options: Options,
    input_fn: InputFn | None = None,
    output_fn: OutputFn | None = None,
) -> Options:
    """Ask for every option in turn, then confirm. Mutates and returns the options."""
    # Resolved here rather than as a default so a caller can swap stdin at run time.
    input_fn = input_fn or input
    output_fn = output_fn or print
    output_fn("yt interactive setup")
    output_fn("Press Enter to accept the value in brackets.")
    output_fn("")

    if not options.urls:
        options.urls = prompts.required("YouTube URL(s), separated by spaces", input_fn).split()

    options.modes = prompts.parsed(
        "Modes: a=audio v=video s=subtitle", options.modes, parse_modes, input_fn, output_fn
    )
    if "s" in options.modes:
        ask_subtitles(options, input_fn, output_fn)
    if "v" in options.modes:
        ask_video(options, input_fn, output_fn)
    if "a" in options.modes:
        ask_audio(options, input_fn, output_fn)
    options.output = prompts.text("Output directory", options.output, input_fn)

    show_summary(options, output_fn)
    if not prompts.yes_no("Start download", True, input_fn, output_fn):
        raise PromptCancelled("cancelled")
    return options


def ask_subtitles(options: Options, input_fn: InputFn, output_fn: OutputFn) -> None:
    """Subtitle languages and output formats."""
    options.sub_langs = prompts.word_list(
        "Subtitle languages (comma separated, or all)", options.sub_langs, input_fn
    )
    options.sub_formats = prompts.subset(
        "Subtitle formats", options.sub_formats, SUBTITLE_FORMATS, input_fn, output_fn
    )


def ask_video(options: Options, input_fn: InputFn, output_fn: OutputFn) -> None:
    """Video height cap and container."""
    options.video_quality = prompts.choice(
        "Video quality", VIDEO_QUALITIES, options.video_quality, input_fn, output_fn
    )
    options.video_format = prompts.choice(
        "Video container", VIDEO_FORMATS, options.video_format, input_fn, output_fn
    )


def ask_audio(options: Options, input_fn: InputFn, output_fn: OutputFn) -> None:
    """Audio bitrate and codec."""
    options.audio_quality = prompts.choice(
        "Audio quality (kbps)", AUDIO_QUALITIES, options.audio_quality, input_fn, output_fn
    )
    options.audio_format = prompts.choice(
        "Audio format", AUDIO_FORMATS, options.audio_format, input_fn, output_fn
    )


def show_summary(options: Options, output_fn: OutputFn) -> None:
    """Print what is about to happen before asking for confirmation."""
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
