"""Logging setup under AppData."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from nasa_wallpaper.config import appdata_dir


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    log_path = appdata_dir() / "app.log"
    logger = logging.getLogger("nasa_wallpaper")
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=512_000,
        backupCount=2,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.WARNING)
    logger.addHandler(console)

    return logger
