"""Application configuration stored in the OS user data directory."""

from __future__ import annotations

import json
import os
import sys
from copy import deepcopy
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path
from typing import Any

APP_DIR_NAME = "NASA Wallpaper"
CONFIG_FILENAME = "config.json"


@dataclass
class AppConfig:
    mode: str = "latest"  # "latest" | "random"
    interval_hours: int = 4  # 0 = off
    api_key: str = ""
    min_width: int = 1920
    min_height: int = 1080
    min_file_size_kb: int = 800
    cache_keep: int = 10
    latest_lookback_days: int = 30
    random_max_attempts: int = 40
    skip_startup_update_minutes: int = 20
    auto_check_updates: bool = True
    last_update: str | None = None
    last_image_path: str | None = None
    last_title: str | None = None
    last_date: str | None = None
    last_app_update_check: str | None = None


def appdata_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        path = Path(base) / APP_DIR_NAME if base else Path.home() / "AppData" / "Roaming" / APP_DIR_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        path = Path(xdg) / "nasa-wallpaper" if xdg else Path.home() / ".config" / "nasa-wallpaper"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return appdata_dir() / CONFIG_FILENAME


def default_save_dir() -> Path:
    pictures = Path.home() / "Pictures" / "NASA_APOD"
    pictures.mkdir(parents=True, exist_ok=True)
    return pictures


def _coerce(data: dict[str, Any]) -> AppConfig:
    known = {f.name for f in fields(AppConfig)}
    cleaned = {k: v for k, v in data.items() if k in known}
    cfg = AppConfig(**cleaned)
    if cfg.mode not in ("latest", "random"):
        cfg.mode = "latest"
    if cfg.interval_hours < 0:
        cfg.interval_hours = 0
    # Migrate overly aggressive older defaults.
    if cfg.skip_startup_update_minutes > 30:
        cfg.skip_startup_update_minutes = 20
    if cfg.latest_lookback_days < 30:
        cfg.latest_lookback_days = 30
    return cfg


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        cfg = AppConfig()
        save_config(cfg)
        return cfg
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return AppConfig()
        return _coerce(data)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return AppConfig()


def save_config(config: AppConfig) -> None:
    path = config_path()
    payload = asdict(config)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    tmp.replace(path)


def has_personal_api_key(config: AppConfig) -> bool:
    env_key = os.environ.get("NASA_API_KEY", "").strip()
    if env_key and env_key.upper() != "DEMO_KEY":
        return True
    key = config.api_key.strip()
    return bool(key) and key.upper() != "DEMO_KEY"


def resolve_api_key(config: AppConfig) -> str:
    """Prefer user/env key; fall back to DEMO_KEY for first-run exploration only."""
    env_key = os.environ.get("NASA_API_KEY", "").strip()
    if env_key:
        return env_key
    if config.api_key.strip():
        return config.api_key.strip()
    return "DEMO_KEY"


def recently_updated(config: AppConfig, within_minutes: int | None = None) -> bool:
    if not config.last_update:
        return False
    minutes = within_minutes if within_minutes is not None else config.skip_startup_update_minutes
    try:
        last = datetime.strptime(config.last_update, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return False
    return (datetime.now() - last).total_seconds() < max(0, minutes) * 60


def clone_config(config: AppConfig) -> AppConfig:
    return deepcopy(config)
