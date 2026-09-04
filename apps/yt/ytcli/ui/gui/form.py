"""The input half of the window: everything the user sets before pressing Download."""

from __future__ import annotations

import itertools
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk

from ...models import (
    AUDIO_FORMATS,
    AUDIO_QUALITIES,
    VIDEO_FORMATS,
    VIDEO_QUALITIES,
    AppError,
)
from ...settings import Options
from ...subtitles import SUBTITLE_FORMATS
from ...utils import split_list
from .widgets import PAD, checkbox, group, labelled_combo


class Form:
    """Builds the option widgets and reads them back as an Options object."""

    def __init__(self, root, options: Options) -> None:
        # Counted rather than hard-coded so the window can put its own rows after the last group.
        rows = itertools.count()
        self.urls = self._build_urls(root, next(rows))
        self.modes = self._build_modes(root, options, next(rows))
        self.langs, self.auto_subs, self.sub_formats = self._build_subtitles(root, options, next(rows))
        self.quality = self._build_quality(root, options, next(rows))
        self.output = self._build_output(root, options, next(rows))
        self.rows = next(rows)

    def collect(self) -> Options:
        """Read every widget, raising AppError when the choices do not make sense."""
        modes = "".join(letter for letter, var in self.modes.items() if var.get())
        if not modes:
            raise AppError("Pick at least one of Audio, Video or Subtitles.")
        sub_formats = tuple(name for name, var in self.sub_formats.items() if var.get())
        if "s" in modes and not sub_formats:
            raise AppError("Pick at least one subtitle format.")
        return Options(
            urls=[line.strip() for line in self.urls.get("1.0", "end").splitlines() if line.strip()],
            modes=modes,
            output=self.output.get().strip() or ".",
            sub_langs=split_list(self.langs.get()) or ("en",),
            sub_formats=sub_formats or ("srt",),
            auto_subs=self.auto_subs.get(),
            video_quality=self.quality["video"].get(),
            video_format=self.quality["container"].get(),
            audio_quality=self.quality["audio"].get(),
            audio_format=self.quality["codec"].get(),
        )

    def _build_urls(self, root, row: int):
        frame = group(root, "YouTube URLs (one per line)", row)
        widget = scrolledtext.ScrolledText(frame, height=4)
        widget.pack(fill="both", expand=True, **PAD)
        return widget

    def _build_modes(self, root, options: Options, row: int) -> dict[str, tk.BooleanVar]:
        frame = group(root, "What to download", row)
        labels = (("a", "Audio"), ("v", "Video"), ("s", "Subtitles"))
        return {
            letter: checkbox(frame, label, letter in options.modes, 0, column)
            for column, (letter, label) in enumerate(labels)
        }

    def _build_subtitles(self, root, options: Options, row: int):
        frame = group(root, "Subtitles", row)
        ttk.Label(frame, text="Languages").grid(row=0, column=0, sticky="w", **PAD)
        langs = tk.StringVar(value=",".join(options.sub_langs))
        ttk.Entry(frame, textvariable=langs, width=24).grid(row=0, column=1, sticky="w", **PAD)
        ttk.Label(frame, text="comma separated, or all").grid(row=0, column=2, sticky="w", **PAD)
        auto_subs = checkbox(frame, "include auto-generated captions", options.auto_subs, 1, 0)

        formats_frame = ttk.Frame(frame)
        formats_frame.grid(row=2, column=0, columnspan=3, sticky="w")
        ttk.Label(formats_frame, text="Formats").grid(row=0, column=0, sticky="w", **PAD)
        sub_formats = {
            name: checkbox(formats_frame, name, name in options.sub_formats, 0, column)
            for column, name in enumerate(SUBTITLE_FORMATS, start=1)
        }
        return langs, auto_subs, sub_formats

    def _build_quality(self, root, options: Options, row: int) -> dict[str, tk.StringVar]:
        frame = group(root, "Quality", row)
        return {
            "video": labelled_combo(frame, "Video", VIDEO_QUALITIES, options.video_quality, 0, 0),
            "container": labelled_combo(frame, "Container", VIDEO_FORMATS, options.video_format, 0, 2),
            "audio": labelled_combo(frame, "Audio kbps", AUDIO_QUALITIES, options.audio_quality, 1, 0),
            "codec": labelled_combo(frame, "Codec", AUDIO_FORMATS, options.audio_format, 1, 2),
        }

    def _build_output(self, root, options: Options, row: int) -> tk.StringVar:
        frame = group(root, "Output directory", row)
        frame.columnconfigure(0, weight=1)
        output = tk.StringVar(value=options.output)
        ttk.Entry(frame, textvariable=output).grid(row=0, column=0, sticky="ew", **PAD)
        ttk.Button(frame, text="Browse...", command=lambda: self._browse(output)).grid(row=0, column=1, **PAD)
        return output

    @staticmethod
    def _browse(output: tk.StringVar) -> None:
        """Pick the output directory with the system dialog."""
        chosen = filedialog.askdirectory(initialdir=str(Path(output.get()).expanduser()))
        if chosen:
            output.set(chosen)
