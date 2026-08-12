"""Check GitHub Releases and self-update the installed binary."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests

from nasa_wallpaper import __version__

logger = logging.getLogger("nasa_wallpaper.updater")

GITHUB_REPO = "pcbaaz/NASA-Wallpaper"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"


@dataclass(frozen=True)
class AppUpdate:
    version: str
    tag: str
    asset_name: str
    download_url: str
    html_url: str
    notes: str


def _parse_version(text: str) -> tuple[int, ...]:
    cleaned = text.strip().lstrip("vV")
    parts = re.findall(r"\d+", cleaned)
    if not parts:
        return (0,)
    return tuple(int(p) for p in parts)


def is_newer(remote: str, current: str = __version__) -> bool:
    return _parse_version(remote) > _parse_version(current)


def current_install_path() -> Path | None:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return None


def platform_asset_prefix() -> str | None:
    if sys.platform == "win32":
        return "NASA_Wallpaper-windows-x64"
    if sys.platform == "darwin":
        return "NASA_Wallpaper-macos-arm64"
    if sys.platform.startswith("linux"):
        return "NASA_Wallpaper-linux-x64"
    return None


def check_for_update(timeout: float = 15.0, current_version: str | None = None) -> AppUpdate | None:
    """Return newer release info, or None if up to date / unavailable."""
    current = current_version if current_version is not None else __version__
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"NASA-Wallpaper/{current}",
    }
    try:
        response = requests.get(RELEASES_API, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.warning("Update check failed: %s", exc)
        # #region agent log
        try:
            import json as _json, time as _time
            from pathlib import Path as _P
            _P(r"C:\Users\behna\Projects\NASA-Wallpaper\debug-0a6770.log").open("a", encoding="utf-8").write(
                _json.dumps({"sessionId":"0a6770","hypothesisId":"C","location":"updater.py:check_for_update","message":"update check network fail","data":{"error":str(exc),"current":current},"timestamp":int(_time.time()*1000)}) + "\n"
            )
        except Exception:
            pass
        # #endregion
        raise RuntimeError(f"Could not check for updates: {exc}") from exc

    tag = str(data.get("tag_name") or "")
    version = tag.lstrip("vV")
    newer = bool(version) and is_newer(version, current)
    # #region agent log
    try:
        import json as _json, time as _time
        from pathlib import Path as _P
        _P(r"C:\Users\behna\Projects\NASA-Wallpaper\debug-0a6770.log").open("a", encoding="utf-8").write(
            _json.dumps({"sessionId":"0a6770","hypothesisId":"A","location":"updater.py:check_for_update","message":"update check compared","data":{"tag":tag,"remote":version,"current":current,"is_newer":newer,"frozen":bool(getattr(sys,"frozen",False)),"exe":str(current_install_path())},"timestamp":int(_time.time()*1000)}) + "\n"
        )
    except Exception:
        pass
    # #endregion
    if not version or not newer:
        return None

    prefix = platform_asset_prefix()
    if not prefix:
        raise RuntimeError("Auto-update is not supported on this platform.")

    assets = data.get("assets") or []
    chosen = None
    for asset in assets:
        name = str(asset.get("name") or "")
        if name.startswith(prefix):
            chosen = asset
            break
    if chosen is None:
        raise RuntimeError(
            f"Update {version} is available, but no binary for this OS was found. "
            f"See {RELEASES_PAGE}"
        )

    return AppUpdate(
        version=version,
        tag=tag,
        asset_name=str(chosen.get("name")),
        download_url=str(chosen.get("browser_download_url")),
        html_url=str(data.get("html_url") or RELEASES_PAGE),
        notes=str(data.get("body") or ""),
    )


def download_update(update: AppUpdate, dest_dir: Path | None = None) -> Path:
    dest_dir = dest_dir or Path(tempfile.gettempdir()) / "nasa_wallpaper_update"
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / update.asset_name

    logger.info("Downloading %s", update.download_url)
    with requests.get(update.download_url, stream=True, timeout=120) as response:
        response.raise_for_status()
        tmp = target.with_suffix(target.suffix + ".partial")
        with tmp.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    fh.write(chunk)
        tmp.replace(target)

    if sys.platform != "win32":
        target.chmod(target.stat().st_mode | 0o111)
    return target


def _windows_replace_script(current: Path, new_file: Path) -> Path:
    script = Path(tempfile.gettempdir()) / "nasa_wallpaper_apply_update.bat"
    # Quote paths — install dir contains spaces ("PC BAAZ\\NASA Wallpaper").
    target = str(current).replace('"', "")
    source = str(new_file).replace('"', "")
    # #region agent log
    try:
        import json as _json, time as _time
        from pathlib import Path as _P
        _P(r"C:\Users\behna\Projects\NASA-Wallpaper\debug-0a6770.log").open("a", encoding="utf-8").write(
            _json.dumps({"sessionId":"0a6770","hypothesisId":"D","location":"updater.py:_windows_replace_script","message":"bat paths","data":{"target":target,"source":source,"target_has_space":(" " in target)},"timestamp":int(_time.time()*1000)}) + "\n"
        )
    except Exception:
        pass
    # #endregion
    # Wait for this process to exit, replace exe, relaunch.
    content = f"""@echo off
setlocal
set "TARGET={target}"
set "SOURCE={source}"
:wait
timeout /t 1 /nobreak >nul
tasklist /FI "PID eq {os.getpid()}" | find "{os.getpid()}" >nul
if not errorlevel 1 goto wait
copy /Y "%SOURCE%" "%TARGET%" >nul
if errorlevel 1 (
  echo copy failed > "%TEMP%\\nasa_wallpaper_update_error.txt"
  exit /b 1
)
start "" "%TARGET%"
del "%~f0"
"""
    script.write_text(content, encoding="utf-8")
    return script


def _unix_replace_script(current: Path, new_file: Path) -> Path:
    script = Path(tempfile.gettempdir()) / "nasa_wallpaper_apply_update.sh"
    content = f"""#!/bin/sh
TARGET="{current.as_posix()}"
SOURCE="{new_file.as_posix()}"
PID={os.getpid()}
while kill -0 "$PID" 2>/dev/null; do
  sleep 1
done
cp "$SOURCE" "$TARGET"
chmod +x "$TARGET"
"$TARGET" &
rm -f "$0"
"""
    script.write_text(content, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    return script


def apply_update_and_restart(new_file: Path) -> None:
    """Schedule binary replacement after this process exits, then exit."""
    current = current_install_path()
    if current is None:
        raise RuntimeError(
            "Auto-update only works for packaged builds. "
            f"Download manually: {RELEASES_PAGE}"
        )

    if sys.platform == "win32":
        script = _windows_replace_script(current, new_file)
        subprocess.Popen(
            ["cmd.exe", "/c", str(script)],
            close_fds=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0),
        )
    else:
        script = _unix_replace_script(current, new_file)
        subprocess.Popen(["/bin/sh", str(script)], start_new_session=True)

    logger.info("Update scheduled; restarting into %s", new_file.name)


def install_update(update: AppUpdate) -> None:
    path = download_update(update)
    apply_update_and_restart(path)
