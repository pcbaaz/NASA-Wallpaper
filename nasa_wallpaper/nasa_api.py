"""APOD client based on apod.nasa.gov HTML pages (no NASA API key)."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import date
from html import unescape
from urllib.parse import urljoin

import requests

logger = logging.getLogger("nasa_wallpaper.nasa_api")

APOD_SITE = "https://apod.nasa.gov/apod/"
APOD_START = date(1995, 6, 16)


class NasaApiError(Exception):
    """Raised when an APOD page cannot be fetched or parsed."""

    def __init__(self, message: str, *, status_code: int | None = None, retryable: bool = False) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


@dataclass(frozen=True)
class ApodEntry:
    date: str
    title: str
    explanation: str
    media_type: str
    url: str | None
    hdurl: str | None

    @property
    def image_url(self) -> str | None:
        return self.hdurl or self.url


class NasaApodClient:
    """Fetches APOD metadata/images from the public website."""

    def __init__(self, timeout: float = 45.0, max_retries: int = 3) -> None:
        self.timeout = timeout
        self.max_retries = max(1, max_retries)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "NASA-Wallpaper/2.5 (+https://github.com/pcbaaz/NASA-Wallpaper)",
                "Accept": "text/html,image/avif,image/webp,image/apng,*/*;q=0.8",
            }
        )

    def _request_get(self, url: str, *, timeout: float | None = None) -> requests.Response:
        last_exc: Exception | None = None
        timeout = timeout if timeout is not None else self.timeout
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, timeout=timeout)
                if response.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                return response
            except requests.RequestException as exc:
                last_exc = exc
                logger.warning("APOD request attempt %s/%s failed: %s", attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise NasaApiError(f"Network error: {exc}", retryable=True) from exc
        raise NasaApiError(f"Network error: {last_exc}", retryable=True)

    def get_apod(self, day: date) -> ApodEntry | None:
        page = f"ap{day.strftime('%y%m%d')}.html"
        url = urljoin(APOD_SITE, page)
        response = self._request_get(url)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise NasaApiError(
                f"APOD HTML HTTP {response.status_code}",
                status_code=response.status_code,
                retryable=response.status_code >= 500,
            )

        # APOD pages are historically latin-1 / windows-1252 flavored.
        response.encoding = response.apparent_encoding or "utf-8"
        return self._parse_html(day, response.text)

    def _parse_html(self, day: date, html: str) -> ApodEntry | None:
        has_video = bool(re.search(r"youtube\.com|youtu\.be|<iframe", html, re.I))
        img_match = re.search(
            r'href="((?:https?://apod\.nasa\.gov/apod/)?image/[^"]+\.(?:jpg|jpeg|png|gif))"',
            html,
            re.I,
        )
        if not img_match:
            img_match = re.search(
                r'src="((?:https?://apod\.nasa\.gov/apod/)?image/[^"]+\.(?:jpg|jpeg|png|gif))"',
                html,
                re.I,
            )

        if not img_match:
            if has_video:
                return ApodEntry(
                    date=day.isoformat(),
                    title="Video APOD",
                    explanation="",
                    media_type="video",
                    url=None,
                    hdurl=None,
                )
            return None

        rel = img_match.group(1)
        image_url = rel if rel.startswith("http") else urljoin(APOD_SITE, rel)

        title = f"APOD {day.isoformat()}"
        title_match = re.search(r"<title>\s*APOD:\s*(.+?)\s*</title>", html, re.I | re.S)
        if title_match:
            title = unescape(re.sub(r"\s+", " ", title_match.group(1))).strip()
            # Titles often look like "2026 August 11 – Name"
            title = re.sub(r"^\d{4}\s+[A-Za-z]+\s+\d{1,2}\s*[–\-—:]\s*", "", title).strip() or title

        expl = ""
        expl_match = re.search(
            r"(?:<b>\s*)?Explanation[:\s]*(?:</b>)?\s*(.+?)(?:<p>\s*<center>|<center>|</body>)",
            html,
            re.I | re.S,
        )
        if expl_match:
            raw = re.sub(r"<[^>]+>", " ", expl_match.group(1))
            expl = unescape(re.sub(r"\s+", " ", raw)).strip()

        return ApodEntry(
            date=day.isoformat(),
            title=title,
            explanation=expl,
            media_type="image",
            url=image_url,
            hdurl=image_url,
        )

    def download_bytes(self, url: str) -> bytes:
        response = self._request_get(url, timeout=max(self.timeout, 90.0))
        if response.status_code != 200:
            raise NasaApiError(
                f"Download HTTP {response.status_code}",
                status_code=response.status_code,
                retryable=response.status_code >= 500,
            )
        return response.content
