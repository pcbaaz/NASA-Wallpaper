"""Local image cache under Pictures/NASA_APOD."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image

from nasa_wallpaper.config import default_save_dir
from nasa_wallpaper.nasa_api import ApodEntry
from nasa_wallpaper.platform_util import open_path

logger = logging.getLogger("nasa_wallpaper.cache")


@dataclass
class CachedImage:
    date: str
    title: str
    explanation: str
    url: str
    path: str
    sha256: str
    width: int
    height: int
    size_kb: float


def _slugify(title: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*]', "", title)
    safe = re.sub(r"[^\w\s-]", "", safe, flags=re.UNICODE).strip()
    safe = re.sub(r"[-\s]+", "_", safe)
    return (safe[:80] or "apod").strip("_")


def _to_jpeg_bytes(image_bytes: bytes) -> bytes:
    """Normalize any supported image to JPEG for wallpaper compatibility."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        if img.mode in ("RGBA", "P", "LA"):
            converted = img.convert("RGB")
        else:
            converted = img.convert("RGB") if img.mode != "RGB" else img
        out = io.BytesIO()
        converted.save(out, format="JPEG", quality=92, optimize=True)
        return out.getvalue()


class ImageCache:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_save_dir()
        self.root.mkdir(parents=True, exist_ok=True)

    def known_dates(self) -> set[str]:
        dates: set[str] = set()
        for meta in self.root.glob("apod_*.json"):
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                if date := data.get("date"):
                    dates.add(str(date))
            except (OSError, json.JSONDecodeError):
                continue
        return dates

    def known_hashes(self) -> set[str]:
        hashes: set[str] = set()
        for meta in self.root.glob("apod_*.json"):
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                if digest := data.get("sha256"):
                    hashes.add(str(digest))
            except (OSError, json.JSONDecodeError):
                continue
        return hashes

    def save(
        self,
        entry: ApodEntry,
        image_bytes: bytes,
        *,
        width: int,
        height: int,
    ) -> CachedImage:
        digest = hashlib.sha256(image_bytes).hexdigest()
        jpeg_bytes = _to_jpeg_bytes(image_bytes)
        slug = _slugify(entry.title)
        stem = f"apod_{entry.date}_{slug}"
        image_path = self.root / f"{stem}.jpg"
        meta_path = self.root / f"{stem}.json"

        image_path.write_bytes(jpeg_bytes)

        record = CachedImage(
            date=entry.date,
            title=entry.title,
            explanation=entry.explanation,
            url=entry.image_url or "",
            path=str(image_path),
            sha256=digest,
            width=width,
            height=height,
            size_kb=round(len(jpeg_bytes) / 1024.0, 1),
        )
        meta_path.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
        logger.info("Cached %s -> %s", entry.date, image_path.name)
        return record

    def prune(self, keep: int = 10) -> int:
        keep = max(1, keep)
        images = sorted(
            self.root.glob("apod_*.jpg"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        deleted = 0
        for image_path in images[keep:]:
            meta = image_path.with_suffix(".json")
            try:
                image_path.unlink(missing_ok=True)
                meta.unlink(missing_ok=True)
                deleted += 1
            except OSError as exc:
                logger.warning("Failed to prune %s: %s", image_path, exc)
        return deleted

    def open_folder(self) -> None:
        open_path(self.root)
