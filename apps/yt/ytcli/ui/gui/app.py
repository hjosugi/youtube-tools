from __future__ import annotations

import queue
import threading
from pathlib import Path

from . import __version__
from .config import config_path, save_config
from .download import (
    AUDIO_FORMATS,
    AUDIO_QUALITIES,
    VIDEO_FORMATS,
    VIDEO_QUALITIES,
    download,
)
from .models import AppError, DownloadCancelled
from .options import Options
from .utils import split_list
from .writers import SUBTITLE_FORMATS

PAD = {"padx": 8, "pady": 4}


def run_gui(options: Options | None = None) -> int:
    try:
        import tkinter as tk
    except ImportError as error:
        raise AppError(
            "The GUI needs Tk, which is missing from this Python build.\n"
            "Install it (Debian/Ubuntu: `sudo apt install python3-tk`, "
            "Fedora: `sudo dnf install python3-tkinter`, Arch: `sudo pacman -S tk`) "
            "or use the terminal wizard with `yt -i`."
        ) from error

    root = tk.Tk()
    App(root, options or Options())
    root.mainloop()
    return 0


class App:
    def __init__(self, root, options: Options) -> None:
        import tkinter as tk
        from tkinter import scrolledtext, ttk

        self.tk = tk
        self.ttk = ttk
        self.root = root
        self.messages: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.stop_flag = threading.Event()

        root.title(f"yt {__version__}")
        root.minsize(660, 640)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(6, weight=1)

        self.urls = scrolledtext.ScrolledText(self._group("YouTube URLs (one per line)", 0), height=4)
        self.urls.pack(fill="both", expand=True, **PAD)

        modes = self._group("What to download", 1)
        self.want_audio = tk.BooleanVar(value="a" in options.modes)
        self.want_video = tk.BooleanVar(value="v" in options.modes)
        self.want_subs = tk.BooleanVar(value="s" in options.modes)
        for column, (label, var) in enumerate(
            (("Audio", self.want_audio), ("Video", self.want_video), ("Subtitles", self.want_subs))
        ):
            ttk.Checkbutton(modes, text=label, variable=var).grid(row=0, column=column, sticky="w", **PAD)

        subs = self._group("Subtitles", 2)
        ttk.Label(subs, text="Languages").grid(row=0, column=0, sticky="w", **PAD)
        self.langs = tk.StringVar(value=",".join(options.sub_langs))
        ttk.Entry(subs, textvariable=self.langs, width=24).grid(row=0, column=1, sticky="w", **PAD)
        ttk.Label(subs, text="comma separated, or all").grid(row=0, column=2, sticky="w", **PAD)
        self.auto_subs = tk.BooleanVar(value=options.auto_subs)
        ttk.Checkbutton(subs, text="include auto-generated captions", variable=self.auto_subs).grid(
            row=1, column=0, columnspan=3, sticky="w", **PAD
        )
        formats = ttk.Frame(subs)
        formats.grid(row=2, column=0, columnspan=3, sticky="w")
        ttk.Label(formats, text="Formats").grid(row=0, column=0, sticky="w", **PAD)
        self.sub_formats = {}
        for column, name in enumerate(SUBTITLE_FORMATS, start=1):
            var = tk.BooleanVar(value=name in options.sub_formats)
            self.sub_formats[name] = var
            ttk.Checkbutton(formats, text=name, variable=var).grid(row=0, column=column, sticky="w", padx=4)

        quality = self._group("Quality", 3)
        self.video_quality = self._combo(quality, "Video", VIDEO_QUALITIES, options.video_quality, 0, 0)
        self.video_format = self._combo(quality, "Container", VIDEO_FORMATS, options.video_format, 0, 2)
        self.audio_quality = self._combo(quality, "Audio kbps", AUDIO_QUALITIES, options.audio_quality, 1, 0)
        self.audio_format = self._combo(quality, "Codec", AUDIO_FORMATS, options.audio_format, 1, 2)

        output = self._group("Output directory", 4)
        output.columnconfigure(0, weight=1)
        self.output = tk.StringVar(value=options.output)
        ttk.Entry(output, textvariable=self.output).grid(row=0, column=0, sticky="ew", **PAD)
        ttk.Button(output, text="Browse...", command=self._browse).grid(row=0, column=1, **PAD)

        actions = ttk.Frame(root)
        actions.grid(row=5, column=0, sticky="ew", padx=8)
        self.start_button = ttk.Button(actions, text="Download", command=self._start)
        self.start_button.grid(row=0, column=0, **PAD)
        self.stop_button = ttk.Button(actions, text="Stop", command=self._stop, state="disabled")
        self.stop_button.grid(row=0, column=1, **PAD)
        ttk.Button(actions, text="Save as defaults", command=self._save_defaults).grid(row=0, column=2, **PAD)
        self.status = tk.StringVar(value="Ready")
        ttk.Label(actions, textvariable=self.status).grid(row=0, column=3, sticky="w", **PAD)

        log_frame = self._group("Log", 6)
        self.log = scrolledtext.ScrolledText(log_frame, height=14, state="disabled")
        self.log.pack(fill="both", expand=True, **PAD)

        root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._write(f"Config: {config_path()}")
        self.root.after(120, self._drain)

    def _group(self, title: str, row: int):
        frame = self.ttk.LabelFrame(self.root, text=title)
        frame.grid(row=row, column=0, sticky="nsew", padx=8, pady=4)
        return frame

    def _combo(self, parent, label: str, values, current: str, row: int, column: int):
        self.ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", **PAD)
        var = self.tk.StringVar(value=current)
        box = self.ttk.Combobox(parent, textvariable=var, values=list(values), state="readonly", width=10)
        box.grid(row=row, column=column + 1, sticky="w", **PAD)
        return var

    def _browse(self) -> None:
        from tkinter import filedialog

        chosen = filedialog.askdirectory(initialdir=str(Path(self.output.get()).expanduser()))
        if chosen:
            self.output.set(chosen)

    def _collect_options(self) -> Options:
        modes = "".join(
            letter
            for letter, var in (("a", self.want_audio), ("v", self.want_video), ("s", self.want_subs))
            if var.get()
        )
        if not modes:
            raise AppError("Pick at least one of Audio, Video or Subtitles.")
        sub_formats = tuple(name for name, var in self.sub_formats.items() if var.get())
        if "s" in modes and not sub_formats:
            raise AppError("Pick at least one subtitle format.")
        langs = split_list(self.langs.get()) or ("en",)
        urls = [line.strip() for line in self.urls.get("1.0", "end").splitlines() if line.strip()]
        return Options(
            urls=urls,
            modes=modes,
            output=self.output.get().strip() or ".",
            sub_langs=langs,
            sub_formats=sub_formats or ("srt",),
            auto_subs=self.auto_subs.get(),
            video_quality=self.video_quality.get(),
            video_format=self.video_format.get(),
            audio_quality=self.audio_quality.get(),
            audio_format=self.audio_format.get(),
        )

    def _save_defaults(self) -> None:
        from tkinter import messagebox

        try:
            path = save_config(self._collect_options().to_config())
        except AppError as error:
            messagebox.showerror("yt", str(error))
            return
        self._write(f"Saved defaults to {path}")
        self.status.set("Defaults saved")

    def _start(self) -> None:
        from tkinter import messagebox

        if self.worker and self.worker.is_alive():
            return
        try:
            options = self._collect_options()
        except AppError as error:
            messagebox.showerror("yt", str(error))
            return
        if not options.urls:
            messagebox.showerror("yt", "Enter at least one YouTube URL.")
            return

        self.stop_flag.clear()
        self.start_button.state(["disabled"])
        self.stop_button.state(["!disabled"])
        self.status.set("Downloading...")
        self._write(f"\n=== Output: {options.out_dir}")
        self.worker = threading.Thread(target=self._work, args=(options,), daemon=True)
        self.worker.start()

    def _stop(self) -> None:
        self.stop_flag.set()
        self.status.set("Stopping after the current step...")

    def _work(self, options: Options) -> None:
        def log(line: str) -> None:
            self.messages.put(("log", line))

        saved = 0
        failed = 0
        for url in options.urls:
            if self.stop_flag.is_set():
                log("Stopped.")
                break
            log(f"\n=== {url}")
            try:
                result = download(options.to_request(url), log, self.stop_flag.is_set)
            except DownloadCancelled:
                log("Stopped.")
                break
            except AppError as error:
                log(f"error: {error}")
                failed += 1
                continue
            except Exception as error:  # yt-dlp and ffmpeg raise a wide range of errors
                log(f"unexpected error: {error}")
                failed += 1
                continue
            saved += len(result.files)
            for warning in result.warnings:
                log(f"note: {warning}")
        summary = f"Done. {saved} file(s) saved" + (f", {failed} failed" if failed else "")
        self.messages.put(("done", summary))

    def _drain(self) -> None:
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "log":
                    self._write(payload)
                else:
                    self._write(payload)
                    self.status.set(payload)
                    self.start_button.state(["!disabled"])
                    self.stop_button.state(["disabled"])
        except queue.Empty:
            pass
        self.root.after(120, self._drain)

    def _write(self, line: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", line.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _on_close(self) -> None:
        self.stop_flag.set()
        self.root.destroy()
