"""Tiny Tk settings dialog with NASA API key guide."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from nasa_wallpaper.config import AppConfig, has_personal_api_key, save_config
from nasa_wallpaper.platform_util import NASA_API_SIGNUP_URL, open_url


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

    ttk.Label(frame, text="NASA API Key (required for daily use)", font=("", 10, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w"
    )

    guide = (
        "1) Open api.nasa.gov\n"
        "2) Fill the short form (name + email)\n"
        "3) Copy your free key and paste it below\n"
        "4) Without a personal key, DEMO_KEY is used (very limited)"
    )
    ttk.Label(frame, text=guide, justify="left").grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(6, 10)
    )

    ttk.Button(
        frame,
        text="Open api.nasa.gov to get a free key",
        command=lambda: open_url(NASA_API_SIGNUP_URL),
    ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))

    status = (
        "Status: personal key configured"
        if has_personal_api_key(config)
        else "Status: using DEMO_KEY (get a free personal key)"
    )
    status_label = ttk.Label(frame, text=status)
    status_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 8))

    api_var = tk.StringVar(value=config.api_key)
    api_entry = ttk.Entry(frame, textvariable=api_var, width=44, show="*")
    api_entry.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 6))

    show_var = tk.BooleanVar(value=False)

    def toggle_show() -> None:
        api_entry.configure(show="" if show_var.get() else "*")

    ttk.Checkbutton(frame, text="Show key", variable=show_var, command=toggle_show).grid(
        row=5, column=0, sticky="w", pady=(0, 14)
    )

    ttk.Separator(frame).grid(row=6, column=0, columnspan=2, sticky="ew", pady=(0, 12))

    ttk.Label(frame, text="Min width").grid(row=7, column=0, sticky="w")
    width_var = tk.StringVar(value=str(config.min_width))
    ttk.Entry(frame, textvariable=width_var, width=12).grid(row=7, column=1, sticky="w")

    ttk.Label(frame, text="Min height").grid(row=8, column=0, sticky="w")
    height_var = tk.StringVar(value=str(config.min_height))
    ttk.Entry(frame, textvariable=height_var, width=12).grid(row=8, column=1, sticky="w")

    ttk.Label(frame, text="Min file size (KB)").grid(row=9, column=0, sticky="w")
    size_var = tk.StringVar(value=str(config.min_file_size_kb))
    ttk.Entry(frame, textvariable=size_var, width=12).grid(row=9, column=1, sticky="w")

    ttk.Label(frame, text="Cache keep (images)").grid(row=10, column=0, sticky="w")
    keep_var = tk.StringVar(value=str(config.cache_keep))
    ttk.Entry(frame, textvariable=keep_var, width=12).grid(row=10, column=1, sticky="w")

    def save() -> None:
        try:
            config.api_key = api_var.get().strip()
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
    buttons.grid(row=11, column=0, columnspan=2, pady=(16, 0), sticky="e")
    ttk.Button(buttons, text="Cancel", command=root.destroy).pack(side="right", padx=(8, 0))
    ttk.Button(buttons, text="Save", command=save).pack(side="right")

    root.update_idletasks()
    w, h = root.winfo_reqwidth(), root.winfo_reqheight()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 3
    root.geometry(f"+{x}+{y}")
    root.mainloop()
