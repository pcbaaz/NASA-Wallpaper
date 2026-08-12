"""Tiny Tk settings dialog (quality thresholds)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from nasa_wallpaper.config import AppConfig, save_config
from nasa_wallpaper.platform_util import APOD_HOME_URL, open_url


def open_settings(config: AppConfig, on_saved=None) -> None:
    root = tk.Tk()
    root.title("NASA Wallpaper — Settings")
    root.resizable(False, False)
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frame, text="Image quality filters", font=("", 10, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w"
    )
    ttk.Label(
        frame,
        text="Images are downloaded from apod.nasa.gov (no API key needed).",
        wraplength=360,
        justify="left",
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 10))

    ttk.Button(
        frame,
        text="Open APOD website",
        command=lambda: open_url(APOD_HOME_URL),
    ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 14))

    ttk.Label(frame, text="Min width").grid(row=3, column=0, sticky="w")
    width_var = tk.StringVar(value=str(config.min_width))
    ttk.Entry(frame, textvariable=width_var, width=12).grid(row=3, column=1, sticky="w")

    ttk.Label(frame, text="Min height").grid(row=4, column=0, sticky="w")
    height_var = tk.StringVar(value=str(config.min_height))
    ttk.Entry(frame, textvariable=height_var, width=12).grid(row=4, column=1, sticky="w")

    ttk.Label(frame, text="Min file size (KB)").grid(row=5, column=0, sticky="w")
    size_var = tk.StringVar(value=str(config.min_file_size_kb))
    ttk.Entry(frame, textvariable=size_var, width=12).grid(row=5, column=1, sticky="w")

    ttk.Label(frame, text="Cache keep (images)").grid(row=6, column=0, sticky="w")
    keep_var = tk.StringVar(value=str(config.cache_keep))
    ttk.Entry(frame, textvariable=keep_var, width=12).grid(row=6, column=1, sticky="w")

    def save() -> None:
        try:
            config.min_width = max(800, int(width_var.get()))
            config.min_height = max(600, int(height_var.get()))
            config.min_file_size_kb = max(100, int(size_var.get()))
            config.cache_keep = max(1, int(keep_var.get()))
        except ValueError:
            messagebox.showerror("Invalid input", "Numeric fields must be integers.", parent=root)
            return
        save_config(config)
        if on_saved:
            on_saved(config)
        root.destroy()

    buttons = ttk.Frame(frame)
    buttons.grid(row=7, column=0, columnspan=2, pady=(16, 0), sticky="e")
    ttk.Button(buttons, text="Cancel", command=root.destroy).pack(side="right", padx=(8, 0))
    ttk.Button(buttons, text="Save", command=save).pack(side="right")

    root.update_idletasks()
    w, h = root.winfo_reqwidth(), root.winfo_reqheight()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 3
    root.geometry(f"+{x}+{y}")
    root.mainloop()
