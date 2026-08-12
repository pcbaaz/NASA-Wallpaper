"""Cross-platform helpers: open files/URLs, resource paths, single-instance lock."""

from __future__ import annotations

import atexit
import logging
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

logger = logging.getLogger("nasa_wallpaper.platform_util")

NASA_API_SIGNUP_URL = "https://api.nasa.gov/"
APOD_HOME_URL = "https://apod.nasa.gov/apod/"

_lock_fh = None


def resource_path(relative: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parent.parent
    return base / relative


def open_path(path: str | Path) -> None:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(str(target))
    if sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(target)], check=False)
    else:
        subprocess.run(["xdg-open", str(target)], check=False)


def open_url(url: str) -> None:
    webbrowser.open(url)


def acquire_single_instance(lock_path: Path) -> bool:
    """Return False if another instance already holds the lock."""
    global _lock_fh
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fh = open(lock_path, "a+", encoding="utf-8")  # noqa: SIM115
        if sys.platform == "win32":
            import msvcrt

            try:
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                fh.close()
                return False
        else:
            import fcntl

            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                fh.close()
                return False
        fh.seek(0)
        fh.truncate()
        fh.write(str(os.getpid()))
        fh.flush()
        _lock_fh = fh

        def _release() -> None:
            global _lock_fh
            if _lock_fh is None:
                return
            try:
                if sys.platform == "win32":
                    import msvcrt

                    _lock_fh.seek(0)
                    msvcrt.locking(_lock_fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(_lock_fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                _lock_fh.close()
            except OSError:
                pass
            _lock_fh = None
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass

        atexit.register(_release)
        return True
    except OSError as exc:
        logger.warning("Could not acquire instance lock: %s", exc)
        return True
