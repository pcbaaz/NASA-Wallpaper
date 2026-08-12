"""Background interval scheduler."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

logger = logging.getLogger("nasa_wallpaper.scheduler")


class IntervalScheduler:
    """Runs a callback every N hours on a daemon thread."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._hours = 0
        self._callback: Callable[[], None] | None = None
        self._lock = threading.Lock()

    @property
    def hours(self) -> int:
        return self._hours

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and self._hours > 0

    def start(self, hours: int, callback: Callable[[], None]) -> None:
        with self._lock:
            self.stop(join=False)
            self._hours = max(0, int(hours))
            self._callback = callback
            if self._hours <= 0:
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop,
                name="nasa-wallpaper-scheduler",
                daemon=True,
            )
            self._thread.start()
            logger.info("Scheduler started: every %sh", self._hours)

    def stop(self, join: bool = True) -> None:
        self._stop.set()
        thread = self._thread
        self._hours = 0
        self._thread = None
        if join and thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2)

    def _loop(self) -> None:
        assert self._callback is not None
        interval = max(1, self._hours) * 3600
        # First tick after full interval (manual update covers immediate need)
        while not self._stop.wait(interval):
            try:
                self._callback()
            except Exception:  # noqa: BLE001
                logger.exception("Scheduled update failed")
            # Refresh interval in case it changed mid-run via restart
            interval = max(1, self._hours or 1) * 3600
            if self._hours <= 0:
                break
