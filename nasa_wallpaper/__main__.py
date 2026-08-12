"""Entry point: python -m nasa_wallpaper."""

from __future__ import annotations

import sys


def main() -> int:
    from nasa_wallpaper.config import appdata_dir
    from nasa_wallpaper.logging_setup import setup_logging
    from nasa_wallpaper.platform_util import acquire_single_instance
    from nasa_wallpaper.tray import TrayApp

    setup_logging()
    lock = appdata_dir() / "nasa_wallpaper.lock"
    if not acquire_single_instance(lock):
        print("NASA Wallpaper is already running.", file=sys.stderr)
        return 0

    TrayApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
