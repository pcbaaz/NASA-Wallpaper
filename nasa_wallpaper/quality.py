"""Quality filters to prefer beautiful high-resolution APOD photos."""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass

from PIL import Image

from nasa_wallpaper.nasa_api import ApodEntry

logger = logging.getLogger("nasa_wallpaper.quality")

# Titles/explanations that usually mean charts, slides, or non-scenic media.
SKIP_PATTERNS = [
    r"\bchart\b",
    r"\bdiagram\b",
    r"\bgraph\b",
    r"\bplot\b",
    r"\binfographic\b",
    r"\bschematic\b",
    r"\billustration\b",
    r"\bmap of\b",
    r"\bspectrum\b",
    r"\bhistogram\b",
    r"\bslideshow\b",
    r"\bpresentation\b",
    r"\banimated?\b",
    r"\bgif\b",
    r"\bvideo\b",
    r"\byoutube\b",
    r"\bcomposite labeled\b",
]

_SKIP_RE = re.compile("|".join(SKIP_PATTERNS), re.IGNORECASE)


@dataclass(frozen=True)
class QualityThresholds:
    min_width: int = 1920
    min_height: int = 1080
    min_file_size_kb: int = 800


@dataclass(frozen=True)
class QualityResult:
    ok: bool
    reason: str = ""
    width: int = 0
    height: int = 0
    size_kb: float = 0.0


def passes_metadata_filter(entry: ApodEntry) -> QualityResult:
    if entry.media_type != "image":
        return QualityResult(False, f"media_type={entry.media_type!r}")
    if not entry.image_url:
        return QualityResult(False, "no image url")
    text = f"{entry.title}\n{entry.explanation}"
    match = _SKIP_RE.search(text)
    if match:
        return QualityResult(False, f"skip keyword: {match.group(0)!r}")
    return QualityResult(True)


def evaluate_image_bytes(data: bytes, thresholds: QualityThresholds) -> QualityResult:
    size_kb = len(data) / 1024.0
    if size_kb < thresholds.min_file_size_kb:
        return QualityResult(False, f"file too small ({size_kb:.0f} KB)", size_kb=size_kb)

    try:
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
            img.verify()
    except Exception as exc:  # noqa: BLE001 — bad downloads happen
        return QualityResult(False, f"invalid image: {exc}", size_kb=size_kb)

    if width < 1 or height < 1:
        return QualityResult(False, "invalid dimensions", size_kb=size_kb)

    # Accept landscape or portrait if large enough for desktop Fill.
    # (Many APODs are portrait; rejecting them left Latest stuck on old cache.)
    short_side = min(width, height)
    long_side = max(width, height)
    min_short = min(thresholds.min_width, thresholds.min_height)
    min_long = max(thresholds.min_width, thresholds.min_height)
    if short_side < min_short or long_side < min_long:
        return QualityResult(
            False,
            f"resolution too low ({width}x{height})",
            width=width,
            height=height,
            size_kb=size_kb,
        )

    return QualityResult(True, width=width, height=height, size_kb=size_kb)
