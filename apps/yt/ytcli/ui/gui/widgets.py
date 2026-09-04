"""Small Tk helpers shared by the form and the window."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

PAD = {"padx": 8, "pady": 4}


def group(parent, title: str, row: int):
    """A titled frame occupying one row of the window's single column."""
    frame = ttk.LabelFrame(parent, text=title)
    frame.grid(row=row, column=0, sticky="nsew", padx=8, pady=4)
    return frame


def labelled_combo(parent, label: str, values, current: str, row: int, column: int) -> tk.StringVar:
    """A read-only dropdown with its label, returning the variable holding the choice."""
    ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", **PAD)
    variable = tk.StringVar(value=current)
    box = ttk.Combobox(parent, textvariable=variable, values=list(values), state="readonly", width=10)
    box.grid(row=row, column=column + 1, sticky="w", **PAD)
    return variable


def checkbox(parent, label: str, checked: bool, row: int, column: int) -> tk.BooleanVar:
    """A checkbox, returning the variable holding its state."""
    variable = tk.BooleanVar(value=checked)
    ttk.Checkbutton(parent, text=label, variable=variable).grid(row=row, column=column, sticky="w", **PAD)
    return variable
