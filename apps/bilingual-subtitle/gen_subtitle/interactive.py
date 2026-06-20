from __future__ import annotations

import argparse
from collections.abc import Callable


InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]


class PromptCancelled(Exception):
    pass


def apply_interactive_options(
    args: argparse.Namespace,
    input_fn: InputFn = input,
    output_fn: OutputFn = print,
) -> argparse.Namespace:
    output_fn("Bilingual subtitle interactive setup")
    output_fn("Press Enter to accept the default shown in brackets.")

    if not args.url:
        args.url = prompt_required("YouTube URL", input_fn)

    output_fn("")
    output_fn("Translation mode")
    output_fn("1. Argos local translation")
    output_fn("2. English only")
    output_fn("3. DeepL")
    mode = prompt_choice("Choose mode", choices=("1", "2", "3"), default="1", input_fn=input_fn)
    if mode == "1":
        args.translator = "argos"
        args.en_only = False
    elif mode == "2":
        args.en_only = True
    else:
        args.translator = "deepl"
        args.en_only = False
        if not args.deepl_auth_key:
            args.deepl_auth_key = prompt_required("DeepL auth key", input_fn=input_fn)

    args.out_dir = prompt_text("Output directory", default=args.out_dir, input_fn=input_fn)
    args.output_name = prompt_text("Output base name", default=args.output_name or "auto", input_fn=input_fn)
    if args.output_name == "auto":
        args.output_name = ""
    args.batch_size = prompt_int("Batch size", default=args.batch_size, input_fn=input_fn)

    output_fn("")
    output_fn("Summary")
    output_fn(f"- URL: {args.url}")
    output_fn(f"- mode: {'English only' if args.en_only else args.translator}")
    output_fn(f"- output directory: {args.out_dir}")
    output_fn(f"- output base name: {args.output_name or 'auto'}")
    output_fn(f"- batch size: {args.batch_size}")

    if not prompt_yes_no("Start subtitle generation", default=True, input_fn=input_fn):
        raise PromptCancelled("cancelled")

    return args


def prompt_required(label: str, input_fn: InputFn) -> str:
    while True:
        value = input_fn(f"{label}: ").strip()
        if value:
            return value
        print("Please enter a value.")


def prompt_text(label: str, default: str, input_fn: InputFn) -> str:
    suffix = f" [{default}]" if default else ""
    value = input_fn(f"{label}{suffix}: ").strip()
    return value if value else default


def prompt_choice(label: str, choices: tuple[str, ...], default: str, input_fn: InputFn) -> str:
    choices_text = "/".join(choices)
    while True:
        value = input_fn(f"{label} ({choices_text}) [{default}]: ").strip()
        if not value:
            return default
        if value in choices:
            return value
        print(f"Please choose one of: {choices_text}")


def prompt_int(label: str, default: int, input_fn: InputFn) -> int:
    while True:
        value = input_fn(f"{label} [{default}]: ").strip()
        if not value:
            return default
        try:
            parsed = int(value)
        except ValueError:
            print("Please enter a number.")
            continue
        if parsed > 0:
            return parsed
        print("Please enter a positive number.")


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
