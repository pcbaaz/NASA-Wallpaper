"""NASA APOD client with API + HTML fallback."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.parse import urljoin

import requests

logger = logging.getLogger("nasa_wallpaper.nasa_api")

APOD_URL = "https://api.nasa.gov/planetary/apod"
APOD_SITE = "https://apod.nasa.gov/apod/"
APOD_START = date(1995, 6, 16)


class NasaApiError(Exception):
    """Raised when the NASA API cannot fulfill a request."""

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


def _parse_entry(data: dict[str, Any]) -> ApodEntry:
    return ApodEntry(
        date=str(data.get("date", "")),
        title=str(data.get("title") or "Untitled"),
        explanation=str(data.get("explanation") or ""),
        media_type=str(data.get("media_type") or ""),
        url=data.get("url"),
        hdurl=data.get("hdurl"),
    )


def _safe_exc(exc: BaseException, api_key: str = "") -> str:
    text = str(exc)
    if api_key:
        text = text.replace(api_key, "***")
    # Drop query strings that may contain keys.
    text = re.sub(r"api_key=[^&\s]+", "api_key=***", text)
    return text


class NasaApodClient:
    def __init__(self, api_key: str, timeout: float = 45.0, max_retries: int = 3) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max(1, max_retries)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "NASA-Wallpaper/2.4 (+https://github.com/pcbaaz/NASA-Wallpaper)",
                "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            }
        )

    def _request_get(self, url: str, *, params: dict | None = None, timeout: float | None = None) -> requests.Response:
        last_exc: Exception | None = None
        timeout = timeout if timeout is not None else self.timeout
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=timeout)
                if response.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                return response
            except requests.RequestException as exc:
                last_exc = exc
                logger.warning(
                    "NASA request attempt %s/%s failed: %s",
                    attempt,
                    self.max_retries,
                    _safe_exc(exc, self.api_key),
                )
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise NasaApiError(f"Network error: {_safe_exc(exc, self.api_key)}", retryable=True) from exc
        raise NasaApiError(f"Network error: {_safe_exc(last_exc or Exception('unknown'), self.api_key)}", retryable=True)

    def get_apod(self, day: date) -> ApodEntry | None:
        try:
            return self._get_apod_api(day)
        except NasaApiError as exc:
            logger.warning("API failed for %s (%s); trying APOD HTML fallback", day.isoformat(), exc)
            try:
                return self._get_apod_html(day)
            except NasaApiError:
                # Prefer original API error message for rate-limit / auth issues.
                if exc.status_code in (403, 429):
                    raise exc
                raise

    def _get_apod_api(self, day: date) -> ApodEntry | None:
        params = {"api_key": self.api_key, "date": day.isoformat()}
        response = self._request_get(APOD_URL, params=params)

        if response.status_code == 429:
            raise NasaApiError(
                "NASA API rate limit reached. Get a free personal key at api.nasa.gov (Settings).",
                status_code=429,
                retryable=True,
            )
        if response.status_code == 403:
            raise NasaApiError(
                "NASA API key rejected. Open Settings and paste a valid key from api.nasa.gov.",
                status_code=403,
            )
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise NasaApiError(
                f"NASA API HTTP {response.status_code}",
                status_code=response.status_code,
                retryable=response.status_code >= 500,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise NasaApiError("Invalid JSON from NASA API") from exc

        if isinstance(payload, list):
            if not payload:
                return None
            payload = payload[0]
        if not isinstance(payload, dict):
            return None
        if payload.get("error"):
            msg = payload["error"]
            if isinstance(msg, dict):
                msg = msg.get("message", str(msg))
            raise NasaApiError(str(msg))

        return _parse_entry(payload)

    def _get_apod_html(self, day: date) -> ApodEntry | None:
        """Scrape apod.nasa.gov page when api.nasa.gov is unreachable."""
        page = f"ap{day.strftime('%y%m%d')}.html"
        url = urljoin(APOD_SITE, page)
        response = self._request_get(url)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise NasaApiError(f"APOD HTML HTTP {response.status_code}", status_code=response.status_code, retryable=True)

        html = response.text
        # YouTube / video days
        if re.search(r"youtube\.com|youtu\.be|iframe", html, re.I) and not re.search(
            r'href="(image/[^"]+\.(?:jpg|jpeg|png|gif))"', html, re.I
        ):
            return ApodEntry(
                date=day.isoformat(),
                title="Video APOD",
                explanation="",
                media_type="video",
                url=None,
                hdurl=None,
            )

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
            return None

        rel = img_match.group(1)
        image_url = rel if rel.startswith("http") else urljoin(APOD_SITE, rel)

        title_match = re.search(r"<title>\s*APOD:\s*(.+?)\s*</title>", html, re.I | re.S)
        if not title_match:
            title_match = re.search(r"<b>\s*([^<]{3,200})\s*</b>", html, re.I)
        title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else f"APOD {day.isoformat()}"

        # Rough explanation extraction (optional for beauty filters).
        expl = ""
        expl_match = re.search(r"Explanation[:\s]*</b>\s*(.+?)<p>\s*<center>", html, re.I | re.S)
        if expl_match:
            raw = re.sub(r"<[^>]+>", " ", expl_match.group(1))
            expl = re.sub(r"\s+", " ", raw).strip()

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
