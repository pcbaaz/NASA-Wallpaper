"""NASA APOD API client."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

import requests

logger = logging.getLogger("nasa_wallpaper.nasa_api")

APOD_URL = "https://api.nasa.gov/planetary/apod"
APOD_START = date(1995, 6, 16)


class NasaApiError(Exception):
    """Raised when the NASA API cannot fulfill a request."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


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
    def __init__(self, api_key: str, timeout: float = 20.0) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "NASA-Wallpaper/2.0 (+https://github.com/pcbaaz/NASA-Wallpaper)"}
        )

    def get_apod(self, day: date) -> ApodEntry | None:
        params = {"api_key": self.api_key, "date": day.isoformat()}
        try:
            response = self.session.get(APOD_URL, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise NasaApiError(f"Network error: {exc}") from exc

        if response.status_code == 429:
            raise NasaApiError(
                "NASA API rate limit reached. Get a free personal key at api.nasa.gov (Settings).",
                status_code=429,
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
        try:
            response = self.session.get(url, timeout=max(self.timeout, 45.0), stream=True)
        except requests.RequestException as exc:
            raise NasaApiError(f"Download failed: {exc}") from exc
        if response.status_code != 200:
            raise NasaApiError(f"Download HTTP {response.status_code}", status_code=response.status_code)
        return response.content
