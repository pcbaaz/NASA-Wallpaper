"""Quality filters to prefer beautiful scenic APOD photos."""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass

from PIL import Image, ImageStat

from nasa_wallpaper.nasa_api import ApodEntry

logger = logging.getLogger("nasa_wallpaper.quality")

# Scientific / non-scenic media that looks poor as wallpaper.
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
    r"\bspectrograph\b",
    r"\bhistogram\b",
    r"\bslideshow\b",
    r"\bpresentation\b",
    r"\banimated?\b",
    r"\bgif\b",
    r"\bvideo\b",
    r"\byoutube\b",
    r"\bmontage\b",
    r"\bcomposite\b",
    r"\bcollage\b",
    r"\bfalse[-\s]?colou?rs?\b",
    r"\bmulti[-\s]?wavelength\b",
    r"\bx[-\s]?ray\b",
    r"\bultraviolet\b",
    r"\binfrared map\b",
    r"\blabeled\b",
    r"\bannotated\b",
    r"\binset\b",
    r"\bpanel\b",
    r"\bfigure\b",
    r"\bside[-\s]?by[-\s]?side\b",
    r"\bbefore and after\b",
    r"\bartist(?:'s)? concept\b",
    r"\bcartoon\b",
    r"\bdrawing\b",
    r"\bsimulation\b",
    r"\bmodel of\b",
    r"\bsoho\b",
    r"\bstereo\b",
    r"\bfrom both earth and space\b",
    r"\bcomparison\b",
    r"\bthree .* pairs\b",
    r"\bdiffraction spike\b",
]

# Soft preference: scenic subjects tend to make better wallpapers.
SCENIC_HINTS = [
    r"\bnebula\b",
    r"\bgalaxy\b",
    r"\bmilky way\b",
    r"\baurora\b",
    r"\bmeteor\b",
    r"\bcomet\b",
    r"\bplanet\b",
    r"\bmoon\b",
    r"\bearth\b",
    r"\bsunrise\b",
    r"\bsunset\b",
    r"\bnight sky\b",
    r"\bstarfield\b",
    r"\bcluster\b",
    r"\bcloud\b",
    r"\blandscape\b",
]

_SKIP_RE = re.compile("|".join(SKIP_PATTERNS), re.IGNORECASE)
_SCENIC_RE = re.compile("|".join(SCENIC_HINTS), re.IGNORECASE)


@dataclass(frozen=True)
class QualityThresholds:
    min_width: int = 1920
    min_height: int = 1080
    min_file_size_kb: int = 800
    require_scenic_hint: bool = False
    min_colorfulness: float = 12.0


@dataclass(frozen=True)
class QualityResult:
    ok: bool
    reason: str = ""
    width: int = 0
    height: int = 0
    size_kb: float = 0.0
    colorfulness: float = 0.0


def passes_metadata_filter(entry: ApodEntry, *, require_scenic_hint: bool = False) -> QualityResult:
    if entry.media_type != "image":
        return QualityResult(False, f"media_type={entry.media_type!r}")
    if not entry.image_url:
        return QualityResult(False, "no image url")
    text = f"{entry.title}\n{entry.explanation}"
    match = _SKIP_RE.search(text)
    if match:
        return QualityResult(False, f"skip keyword: {match.group(0)!r}")
    if require_scenic_hint and not _SCENIC_RE.search(text):
        return QualityResult(False, "no scenic subject hint")
    return QualityResult(True)


def _colorfulness(img: Image.Image) -> float:
    """Hasler-Susstrunk style colorfulness; low values = dull/scientific grayscale-ish."""
    rgb = img.convert("RGB").resize((128, 128))
    stat = ImageStat.Stat(rgb)
    # Mean pairwise channel difference approximation using stddev + mean spread
    r, g, b = stat.mean
    rs, gs, bs = stat.stddev
    rg = abs(r - g)
    yb = abs(0.5 * (r + g) - b)
    return float((rg + yb) / 2.0 + (rs + gs + bs) / 6.0)


def evaluate_image_bytes(data: bytes, thresholds: QualityThresholds) -> QualityResult:
    size_kb = len(data) / 1024.0
    if size_kb < thresholds.min_file_size_kb:
        return QualityResult(False, f"file too small ({size_kb:.0f} KB)", size_kb=size_kb)

    try:
        with Image.open(io.BytesIO(data)) as img:
            width, height = img.size
            colorfulness = _colorfulness(img)
            img.verify()
    except Exception as exc:  # noqa: BLE001 — bad downloads happen
        return QualityResult(False, f"invalid image: {exc}", size_kb=size_kb)

    if width < 1 or height < 1:
        return QualityResult(False, "invalid dimensions", size_kb=size_kb)

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
            colorfulness=colorfulness,
        )

    if colorfulness < thresholds.min_colorfulness:
        return QualityResult(
            False,
            f"too dull/low-color ({colorfulness:.1f})",
            width=width,
            height=height,
            size_kb=size_kb,
            colorfulness=colorfulness,
        )

    return QualityResult(
        True,
        width=width,
        height=height,
        size_kb=size_kb,
        colorfulness=colorfulness,
    )
