"""Core wallpaper update service: latest + random modes with quality filtering."""

from __future__ import annotations

import hashlib
import json
import logging
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from nasa_wallpaper.cache import ImageCache
from nasa_wallpaper.config import AppConfig, resolve_api_key, save_config
from nasa_wallpaper.nasa_api import APOD_START, NasaApiError, NasaApodClient
from nasa_wallpaper.quality import QualityThresholds, evaluate_image_bytes, passes_metadata_filter
from nasa_wallpaper.wallpaper import set_wallpaper

logger = logging.getLogger("nasa_wallpaper.service")


@dataclass(frozen=True)
class UpdateResult:
    ok: bool
    message: str
    title: str | None = None
    path: str | None = None
    date: str | None = None


class WallpaperService:
    def __init__(self, config: AppConfig, cache: ImageCache | None = None) -> None:
        self.config = config
        self.cache = cache or ImageCache()

    def refresh_config(self, config: AppConfig) -> None:
        self.config = config

    def update(self) -> UpdateResult:
        mode = self.config.mode
        try:
            if mode == "random":
                return self._update_random()
            return self._update_latest()
        except NasaApiError as exc:
            logger.error("API error: %s", exc)
            return UpdateResult(False, str(exc))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Update failed")
            return UpdateResult(False, f"Error: {exc}")

    def _client(self) -> NasaApodClient:
        return NasaApodClient(resolve_api_key(self.config))

    def _thresholds(self) -> QualityThresholds:
        return QualityThresholds(
            min_width=self.config.min_width,
            min_height=self.config.min_height,
            min_file_size_kb=self.config.min_file_size_kb,
        )

    def _update_latest(self) -> UpdateResult:
        client = self._client()
        known_dates = self.cache.known_dates()
        known_hashes = self.cache.known_hashes()
        lookback = max(30, self.config.latest_lookback_days)
        today = date.today()
        cached_fallback_day: date | None = None

        for offset in range(lookback):
            day = today - timedelta(days=offset)
            key = day.isoformat()
            if key in known_dates:
                if cached_fallback_day is None:
                    cached_fallback_day = day
                continue
            result = self._try_day(client, day, known_hashes, allow_cached_date=False)
            if result.ok:
                return result
            logger.info("Latest skip %s: %s", day, result.message)

        if cached_fallback_day is not None:
            reapplied = self._reapply_cached(cached_fallback_day.isoformat())
            if reapplied is not None:
                return reapplied

        return UpdateResult(False, f"No high-quality image in the last {lookback} days.")

    def _reapply_cached(self, day: str) -> UpdateResult | None:
        for meta_path in self.cache.root.glob(f"apod_{day}_*.json"):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                path = data.get("path")
                if not path or not Path(path).exists():
                    path = str(meta_path.with_suffix(".jpg"))
                if not Path(path).exists():
                    continue
                set_wallpaper(path)
                self.config.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.config.last_image_path = path
                self.config.last_title = data.get("title")
                self.config.last_date = data.get("date", day)
                save_config(self.config)
                return UpdateResult(
                    True,
                    f"Reapplied: {data.get('title', day)}",
                    title=data.get("title"),
                    path=path,
                    date=data.get("date", day),
                )
            except Exception:  # noqa: BLE001
                logger.exception("Failed to reapply cached %s", meta_path)
        return None

    def _update_random(self) -> UpdateResult:
        client = self._client()
        known_dates = self.cache.known_dates()
        known_hashes = self.cache.known_hashes()
        attempts = max(5, self.config.random_max_attempts)
        today = date.today()
        span = (today - APOD_START).days

        tried: set[str] = set()
        last_reason = "No candidate found"

        for _ in range(attempts):
            day = APOD_START + timedelta(days=random.randint(0, span))
            key = day.isoformat()
            if key in tried:
                continue
            tried.add(key)
            if key in known_dates:
                last_reason = f"{key} already cached"
                continue
            result = self._try_day(client, day, known_hashes, allow_cached_date=False)
            if result.ok:
                return result
            last_reason = result.message

        return UpdateResult(False, f"No suitable random image after {attempts} tries. ({last_reason})")

    def _try_day(
        self,
        client: NasaApodClient,
        day: date,
        known_hashes: set[str],
        *,
        allow_cached_date: bool,
    ) -> UpdateResult:
        try:
            entry = client.get_apod(day)
        except NasaApiError as exc:
            # Keep looping other days instead of aborting the whole update.
            return UpdateResult(False, str(exc))

        if entry is None:
            return UpdateResult(False, "APOD not found")

        meta = passes_metadata_filter(entry)
        if not meta.ok:
            return UpdateResult(False, meta.reason)

        assert entry.image_url
        try:
            data = client.download_bytes(entry.image_url)
        except NasaApiError as exc:
            return UpdateResult(False, str(exc))

        quality = evaluate_image_bytes(data, self._thresholds())
        if not quality.ok:
            return UpdateResult(False, quality.reason)

        digest = hashlib.sha256(data).hexdigest()
        if digest in known_hashes and not allow_cached_date:
            return UpdateResult(False, "duplicate image hash")

        cached = self.cache.save(
            entry,
            data,
            width=quality.width,
            height=quality.height,
        )
        set_wallpaper(cached.path)
        self.cache.prune(self.config.cache_keep)

        self.config.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.config.last_image_path = cached.path
        self.config.last_title = entry.title
        self.config.last_date = entry.date
        save_config(self.config)

        size_mb = cached.size_kb / 1024.0
        return UpdateResult(
            True,
            f"{entry.title} ({size_mb:.2f} MB)",
            title=entry.title,
            path=cached.path,
            date=entry.date,
        )
