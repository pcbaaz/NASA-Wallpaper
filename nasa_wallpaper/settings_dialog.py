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
        row=0, column=0, columnspan=3, sticky="w"
    )

    guide = (
        "1) Open api.nasa.gov\n"
        "2) Fill the short form (name + email)\n"
        "3) Copy your key, then click Paste key (or Ctrl+V)\n"
        "4) Without a personal key, DEMO_KEY is used (very limited)"
    )
    ttk.Label(frame, text=guide, justify="left").grid(
        row=1, column=0, columnspan=3, sticky="w", pady=(6, 10)
    )

    ttk.Button(
        frame,
        text="Open api.nasa.gov to get a free key",
        command=lambda: open_url(NASA_API_SIGNUP_URL),
    ).grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 12))

    status = (
        "Status: personal key configured"
        if has_personal_api_key(config)
        else "Status: using DEMO_KEY (get a free personal key)"
    )
    ttk.Label(frame, text=status).grid(row=3, column=0, columnspan=3, sticky="w", pady=(0, 8))

    # Use classic tk.Entry — ttk.Entry often breaks Ctrl+V paste on Windows.
    api_var = tk.StringVar(value=config.api_key)
    api_entry = tk.Entry(frame, textvariable=api_var, width=48, show="")
    api_entry.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 6))

    show_var = tk.BooleanVar(value=True)

    def toggle_show() -> None:
        api_entry.configure(show="" if show_var.get() else "*")

    def paste_from_clipboard(event=None):  # noqa: ARG001
        try:
            text = root.clipboard_get()
        except tk.TclError:
            messagebox.showwarning(
                "Clipboard empty",
                "Copy your API key first, then click Paste key.",
                parent=root,
            )
            return "break"
        text = (text or "").strip().replace("\r", "").replace("\n", "")
        if not text:
            messagebox.showwarning("Clipboard empty", "No text found on the clipboard.", parent=root)
            return "break"
        api_entry.delete(0, tk.END)
        api_entry.insert(0, text)
        api_entry.icursor(tk.END)
        api_entry.focus_set()
        return "break"

    def clear_key() -> None:
        api_var.set("")
        api_entry.focus_set()

    key_actions = ttk.Frame(frame)
    key_actions.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 14))
    ttk.Button(key_actions, text="Paste key", command=paste_from_clipboard).pack(side="left")
    ttk.Button(key_actions, text="Clear", command=clear_key).pack(side="left", padx=(8, 0))
    ttk.Checkbutton(key_actions, text="Show key", variable=show_var, command=toggle_show).pack(
        side="left", padx=(12, 0)
    )

    # Explicit paste bindings (Windows Tk often ignores default Ctrl+V on entries).
    for seq in ("<Control-v>", "<Control-V>", "<Shift-Insert>", "<Control-Insert>"):
        api_entry.bind(seq, paste_from_clipboard)
    root.bind_all("<Control-v>", paste_from_clipboard)
    root.bind_all("<Control-V>", paste_from_clipboard)

    menu = tk.Menu(root, tearoff=0)
    menu.add_command(label="Paste", command=paste_from_clipboard)
    menu.add_command(label="Clear", command=clear_key)

    def show_menu(event) -> None:
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    api_entry.bind("<Button-3>", show_menu)

    ttk.Separator(frame).grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0, 12))

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
        try:
            root.unbind_all("<Control-v>")
            root.unbind_all("<Control-V>")
        except tk.TclError:
            pass
        root.destroy()

    def on_close() -> None:
        try:
            root.unbind_all("<Control-v>")
            root.unbind_all("<Control-V>")
        except tk.TclError:
            pass
        root.destroy()

    buttons = ttk.Frame(frame)
    buttons.grid(row=11, column=0, columnspan=3, pady=(16, 0), sticky="e")
    ttk.Button(buttons, text="Cancel", command=on_close).pack(side="right", padx=(8, 0))
    ttk.Button(buttons, text="Save", command=save).pack(side="right")

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.update_idletasks()
    w, h = root.winfo_reqwidth(), root.winfo_reqheight()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 3
    root.geometry(f"+{x}+{y}")

    def focus_entry() -> None:
        try:
            root.lift()
            root.focus_force()
            api_entry.focus_set()
            api_entry.selection_range(0, tk.END)
        except tk.TclError:
            pass

    root.after(50, focus_entry)
    root.after(200, focus_entry)
    root.mainloop()
