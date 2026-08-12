"""NASA APOD API client."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

import requests

logger = logging.getLogger("nasa_wallpaper.nasa_api")

APOD_URL = "https://api.nasa.gov/planetary/apod"
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


class NasaApodClient:
    def __init__(self, api_key: str, timeout: float = 45.0, max_retries: int = 3) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max(1, max_retries)
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "NASA-Wallpaper/2.3 (+https://github.com/pcbaaz/NASA-Wallpaper)"}
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
                safe = str(exc)
                if self.api_key:
                    safe = safe.replace(self.api_key, "***")
                logger.warning("NASA request attempt %s/%s failed: %s", attempt, self.max_retries, safe)
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise NasaApiError(f"Network error: {exc}", retryable=True) from exc
        raise NasaApiError(f"Network error: {last_exc}", retryable=True)

    def get_apod(self, day: date) -> ApodEntry | None:
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

    def download_bytes(self, url: str) -> bytes:
        response = self._request_get(url, timeout=max(self.timeout, 90.0))
        if response.status_code != 200:
            raise NasaApiError(
                f"Download HTTP {response.status_code}",
                status_code=response.status_code,
                retryable=response.status_code >= 500,
            )
        return response.content
