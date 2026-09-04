from __future__ import annotations

from collections.abc import Callable

from ..models import AppError
from ..utils import split_list

InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]


class PromptCancelled(Exception):
    """Raised when the user declines the final confirmation."""


def required(label: str, input_fn: InputFn) -> str:
    """Keep asking until something non-empty is typed."""
    while True:
        value = input_fn(f"{label}: ").strip()
        if value:
            return value


def text(label: str, default: str, input_fn: InputFn) -> str:
    """Ask for free text, keeping the default on an empty answer."""
    return input_fn(f"{label} [{default}]: ").strip() or default


def parsed(label: str, default: str, parse, input_fn: InputFn, output_fn: OutputFn) -> str:
    """Ask until the answer survives the given parser."""
    while True:
        try:
            return parse(input_fn(f"{label} [{default}]: ").strip() or default)
        except AppError as error:
            output_fn(str(error))


def word_list(label: str, default: tuple[str, ...], input_fn: InputFn) -> tuple[str, ...]:
    """Ask for a comma separated list, keeping the default on an empty answer."""
    answer = input_fn(f"{label} [{','.join(default)}]: ").strip()
    return split_list(answer) if answer else default


def subset(
    label: str,
    default: tuple[str, ...],
    allowed: tuple[str, ...],
    input_fn: InputFn,
    output_fn: OutputFn,
) -> tuple[str, ...]:
    """Ask for several values out of a fixed set."""
    while True:
        answer = input_fn(f"{label} ({'/'.join(allowed)}) [{','.join(default)}]: ").strip()
        if not answer:
            return default
        chosen = split_list(answer)
        unknown = [item for item in chosen if item not in allowed]
        if not unknown:
            return chosen
        output_fn(f"Unknown value(s): {', '.join(unknown)}")


def choice(
    label: str,
    choices: tuple[str, ...],
    default: str,
    input_fn: InputFn,
    output_fn: OutputFn,
) -> str:
    """Ask for exactly one value out of a fixed set."""
    while True:
        answer = input_fn(f"{label} ({'/'.join(choices)}) [{default}]: ").strip()
        if not answer:
            return default
        if answer in choices:
            return answer
        output_fn(f"Please choose one of: {'/'.join(choices)}")


def yes_no(label: str, default: bool, input_fn: InputFn, output_fn: OutputFn) -> bool:
    """Ask a yes/no question."""
    suffix = "Y/n" if default else "y/N"
    while True:
        answer = input_fn(f"{label} [{suffix}]: ").strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        output_fn("Please answer y or n.")
