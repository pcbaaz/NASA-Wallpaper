"""Set desktop wallpaper on Windows, macOS, and Linux."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("nasa_wallpaper.wallpaper")


def set_wallpaper(image_path: str | Path) -> None:
    path = Path(image_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Wallpaper file not found: {path}")

    if sys.platform == "win32":
        _set_windows(path)
    elif sys.platform == "darwin":
        _set_macos(path)
    else:
        _set_linux(path)
    logger.info("Wallpaper set: %s", path)


def _set_windows(path: Path) -> None:
    import ctypes

    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Desktop",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "10")
            winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")
    except OSError as exc:
        logger.warning("Could not set wallpaper style registry: %s", exc)

    ok = ctypes.windll.user32.SystemParametersInfoW(20, 0, str(path), 0x01 | 0x02)
    if not ok:
        raise OSError("SystemParametersInfoW failed to set wallpaper")


def _set_macos(path: Path) -> None:
    script = f'''
    tell application "System Events"
        set picture of every desktop to POSIX file "{path.as_posix()}"
    end tell
    '''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise OSError(result.stderr.strip() or "osascript failed to set wallpaper")


def _set_linux(path: Path) -> None:
    uri = path.as_uri()
    attempts = [
        [
            "gsettings",
            "set",
            "org.gnome.desktop.background",
            "picture-uri",
            uri,
        ],
        [
            "gsettings",
            "set",
            "org.gnome.desktop.background",
            "picture-uri-dark",
            uri,
        ],
        ["plasma-apply-wallpaperimage", str(path)],
        ["feh", "--bg-fill", str(path)],
        ["nitrogen", "--set-zoom-fill", "--save", str(path)],
        ["swaybg", "-i", str(path), "-m", "fill"],
    ]
    errors: list[str] = []
    for cmd in attempts:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return
            errors.append(f"{cmd[0]}: {result.stderr.strip() or result.returncode}")
        except FileNotFoundError:
            errors.append(f"{cmd[0]}: not found")
            continue
    raise OSError(
        "Could not set Linux wallpaper. Tried gsettings/plasma/feh/nitrogen/swaybg. "
        + "; ".join(errors[:3])
    )
