from __future__ import annotations

from .models import AppError

# One letter per download mode; the tuple order is also the order we print them in.
MODE_NAMES = {"a": "audio", "v": "video", "s": "subtitle"}
MODE_LETTERS: tuple[str, ...] = tuple(MODE_NAMES)
ALL_MODES = "".join(MODE_LETTERS)

# Spellings accepted in place of a letter, on top of the canonical names above.
MODE_ALIASES = {
    **{name: letter for letter, name in MODE_NAMES.items()},
    "sound": "a",
    "mp3": "a",
    "movie": "v",
    "mp4": "v",
    "subtitles": "s",
    "sub": "s",
    "subs": "s",
}


def parse_modes(value: str) -> str:
    """Accept 'avs', 'a,v,s', 'audio,video' or 'all' and return the letters in a fixed order."""
    text = (value or "").strip().lower()
    if not text:
        raise AppError("No mode given. Use -m with any of a (audio), v (video), s (subtitle).")
    if text == "all":
        return ALL_MODES

    letters: set[str] = set()
    for token in (part.strip() for part in text.replace("+", ",").split(",") if part.strip()):
        if token in MODE_ALIASES:
            letters.add(MODE_ALIASES[token])
            continue
        for char in token:
            if char not in MODE_NAMES:
                raise AppError(
                    f"Unknown mode {char!r} in {value!r}. Use a (audio), v (video), s (subtitle) or all."
                )
            letters.add(char)

    ordered = "".join(letter for letter in MODE_LETTERS if letter in letters)
    if not ordered:
        raise AppError(f"No usable mode found in {value!r}.")
    return ordered


def describe_modes(modes: str) -> str:
    """Turn 'avs' into 'audio, video, subtitle' for summaries."""
    return ", ".join(MODE_NAMES[letter] for letter in modes) or "nothing"
