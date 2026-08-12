"""Opt-in run-at-startup helpers for Windows, macOS, and Linux."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger("nasa_wallpaper.startup")

VALUE_NAME = "NASAWallpaper"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _launch_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script = Path(__file__).resolve().parent.parent / "run.py"
    if script.exists():
        return f'"{sys.executable}" "{script}"'
    return f'"{sys.executable}" -m nasa_wallpaper'


def _autostart_desktop_path() -> Path:
    return Path.home() / ".config" / "autostart" / "nasa-wallpaper.desktop"


def _macos_plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / "com.pcbaaz.nasa-wallpaper.plist"


def is_startup_enabled() -> bool:
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, VALUE_NAME)
            return True
        except OSError:
            return False
    if sys.platform == "darwin":
        return _macos_plist_path().exists()
    return _autostart_desktop_path().exists()


def enable_startup() -> bool:
    try:
        if sys.platform == "win32":
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _launch_command())
        elif sys.platform == "darwin":
            exe = sys.executable
            args = [exe, "-m", "nasa_wallpaper"]
            if getattr(sys, "frozen", False):
                args = [exe]
            plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.pcbaaz.nasa-wallpaper</string>
  <key>ProgramArguments</key>
  <array>
    {''.join(f'<string>{a}</string>' for a in args)}
  </array>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
"""
            path = _macos_plist_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(plist, encoding="utf-8")
        else:
            path = _autostart_desktop_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            cmd = _launch_command().replace('"', "")
            path.write_text(
                "\n".join(
                    [
                        "[Desktop Entry]",
                        "Type=Application",
                        "Name=NASA Wallpaper",
                        f"Exec={cmd}",
                        "X-GNOME-Autostart-enabled=true",
                        "NoDisplay=false",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
        logger.info("Startup enabled")
        return True
    except OSError as exc:
        logger.error("Failed to enable startup: %s", exc)
        return False


def disable_startup() -> bool:
    try:
        if sys.platform == "win32":
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, VALUE_NAME)
        elif sys.platform == "darwin":
            _macos_plist_path().unlink(missing_ok=True)
        else:
            _autostart_desktop_path().unlink(missing_ok=True)
        logger.info("Startup disabled")
        return True
    except FileNotFoundError:
        return True
    except OSError as exc:
        logger.error("Failed to disable startup: %s", exc)
        return False


def toggle_startup() -> bool:
    if is_startup_enabled():
        disable_startup()
        return False
    enable_startup()
    return True
