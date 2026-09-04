"""The window itself: buttons, log pane and the background download thread."""

from __future__ import annotations

import queue
import threading
from tkinter import StringVar, messagebox, scrolledtext, ttk

from ... import __version__
from ...download import download_all
from ...models import AppError
from ...settings import Options, config_path, save_config
from .form import Form
from .widgets import PAD, group

DRAIN_INTERVAL_MS = 120


class App:
    """Wires the form to a worker thread and streams its log back into the window."""

    def __init__(self, root, options: Options) -> None:
        self.root = root
        self.messages: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.stop_flag = threading.Event()

        root.title(f"yt {__version__}")
        root.minsize(660, 640)
        root.columnconfigure(0, weight=1)

        self.form = Form(root, options)
        log_row = self.form.rows + 1
        root.rowconfigure(log_row, weight=1)  # the log pane absorbs any spare height
        self._build_actions(root, self.form.rows)
        self._build_log(root, log_row)

        root.protocol("WM_DELETE_WINDOW", self.close)
        self.write(f"Config: {config_path()}")
        self.root.after(DRAIN_INTERVAL_MS, self.drain)

    def _build_actions(self, root, row: int) -> None:
        """The Download / Stop / Save row."""
        frame = ttk.Frame(root)
        frame.grid(row=row, column=0, sticky="ew", padx=8)
        self.start_button = ttk.Button(frame, text="Download", command=self.start)
        self.start_button.grid(row=0, column=0, **PAD)
        self.stop_button = ttk.Button(frame, text="Stop", command=self.stop, state="disabled")
        self.stop_button.grid(row=0, column=1, **PAD)
        ttk.Button(frame, text="Save as defaults", command=self.save_defaults).grid(row=0, column=2, **PAD)
        self.status = StringVar(value="Ready")
        ttk.Label(frame, textvariable=self.status).grid(row=0, column=3, sticky="w", **PAD)

    def _build_log(self, root, row: int) -> None:
        """The read-only output pane."""
        frame = group(root, "Log", row)
        self.log = scrolledtext.ScrolledText(frame, height=14, state="disabled")
        self.log.pack(fill="both", expand=True, **PAD)

    def save_defaults(self) -> None:
        """Store the current form as the config file defaults."""
        try:
            path = save_config(self.form.collect().to_config())
        except AppError as error:
            messagebox.showerror("yt", str(error))
            return
        self.write(f"Saved defaults to {path}")
        self.status.set("Defaults saved")

    def start(self) -> None:
        """Validate the form and hand the URLs to a worker thread."""
        if self.worker and self.worker.is_alive():
            return
        try:
            options = self.form.collect()
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
        self.write(f"\n=== Output: {options.out_dir}")
        self.worker = threading.Thread(target=self.work, args=(options,), daemon=True)
        self.worker.start()

    def stop(self) -> None:
        """Ask the worker to stop at the next checkpoint."""
        self.stop_flag.set()
        self.status.set("Stopping after the current step...")

    def work(self, options: Options) -> None:
        """Runs off the main thread: never touch a widget from here, only the queue."""

        def log(line: str) -> None:
            self.messages.put(("log", line))

        report = download_all(options, log, cancelled=self.stop_flag.is_set)
        if report.cancelled:
            log("Stopped.")
        summary = f"Done. {report.saved} file(s) saved" + (
            f", {report.failed} failed" if report.failed else ""
        )
        self.messages.put(("done", summary))

    def drain(self) -> None:
        """Move queued worker messages into the log pane on the main thread."""
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                self.write(payload)
                if kind == "done":
                    self.finish(payload)
        except queue.Empty:
            pass
        self.root.after(DRAIN_INTERVAL_MS, self.drain)

    def finish(self, summary: str) -> None:
        """Put the buttons back once the worker is done."""
        self.status.set(summary)
        self.start_button.state(["!disabled"])
        self.stop_button.state(["disabled"])

    def write(self, line: str) -> None:
        """Append one line to the read-only log pane."""
        self.log.configure(state="normal")
        self.log.insert("end", line.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def close(self) -> None:
        """Stop any worker and close the window."""
        self.stop_flag.set()
        self.root.destroy()
