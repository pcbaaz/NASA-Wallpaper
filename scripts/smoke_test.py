"""Offline smoke checks (no NASA network calls)."""

from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image

from nasa_wallpaper.nasa_api import ApodEntry
from nasa_wallpaper.quality import QualityThresholds, evaluate_image_bytes, passes_metadata_filter
from nasa_wallpaper.updater import is_newer


def _jpeg_bytes(width: int, height: int, quality: int = 90) -> bytes:
    img = Image.new("RGB", (width, height), color=(20, 40, 80))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def main() -> int:
    chart = ApodEntry(
        date="2020-01-01",
        title="Spectrum Chart of Star X",
        explanation="A diagram of emission lines",
        media_type="image",
        url="https://example.com/a.jpg",
        hdurl="https://example.com/a.jpg",
    )
    photo = ApodEntry(
        date="2020-01-02",
        title="Orion Nebula",
        explanation="A deep field view of glowing gas clouds",
        media_type="image",
        url="https://example.com/b.jpg",
        hdurl="https://example.com/b.jpg",
    )
    video = ApodEntry(
        date="2020-01-03",
        title="Flythrough",
        explanation="A video tour",
        media_type="video",
        url="https://youtube.com/watch?v=1",
        hdurl=None,
    )

    assert not passes_metadata_filter(chart).ok, "chart should fail"
    assert passes_metadata_filter(photo).ok, "photo should pass"
    assert not passes_metadata_filter(video).ok, "video should fail"

    thresholds = QualityThresholds(min_width=1920, min_height=1080, min_file_size_kb=50)
    good = evaluate_image_bytes(_jpeg_bytes(2560, 1440, quality=95), thresholds)
    bad_res = evaluate_image_bytes(_jpeg_bytes(800, 600, quality=95), thresholds)
    assert good.ok, good.reason
    assert not bad_res.ok, "low res should fail"

    assert is_newer("2.2.0", "2.1.1")
    assert not is_newer("2.1.1", "2.2.0")
    assert not is_newer("2.2.0", "2.2.0")

    print("smoke_test: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
