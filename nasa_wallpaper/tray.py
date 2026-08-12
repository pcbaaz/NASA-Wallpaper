"""System tray UI for NASA Wallpaper."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as Item

from nasa_wallpaper import APP_NAME, __version__
from nasa_wallpaper.cache import ImageCache
from nasa_wallpaper.config import (
    AppConfig,
    has_personal_api_key,
    load_config,
    recently_updated,
    save_config,
)
from nasa_wallpaper.platform_util import (
    NASA_API_SIGNUP_URL,
    open_path,
    open_url,
    resource_path,
)
from nasa_wallpaper.scheduler import IntervalScheduler
from nasa_wallpaper.service import UpdateResult, WallpaperService
from nasa_wallpaper.settings_dialog import open_settings
from nasa_wallpaper.startup import is_startup_enabled, toggle_startup
from nasa_wallpaper.updater import (
    RELEASES_PAGE,
    AppUpdate,
    check_for_update,
    current_install_path,
    install_update,
)

logger = logging.getLogger("nasa_wallpaper.tray")

INTERVAL_CHOICES = (0, 1, 4, 12, 24)


def load_tray_image() -> Image.Image:
    for name in ("assets/icon.png", "assets/icon.ico"):
        icon_path = resource_path(name)
        if not icon_path.exists():
            continue
        try:
            img = Image.open(icon_path)
            return img.convert("RGBA")
        except OSError:
            logger.warning("Could not open %s", icon_path)
    img = Image.new("RGBA", (64, 64), (11, 14, 23, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((6, 6, 58, 58), fill=(11, 61, 145, 255))
    draw.ellipse((18, 18, 46, 46), fill=(255, 107, 53, 255))
    draw.ellipse((28, 28, 36, 36), fill=(232, 237, 245, 255))
    return img


class TrayApp:
    def __init__(self) -> None:
        self.config = load_config()
        self.cache = ImageCache()
        self.service = WallpaperService(self.config, self.cache)
        self.scheduler = IntervalScheduler()
        self.icon: pystray.Icon | None = None
        self._busy = False
        self._busy_lock = threading.Lock()
        self._pending_app_update: AppUpdate | None = None
        self._app_update_busy = False

    def run(self) -> None:
        self.icon = pystray.Icon(
            "nasa_wallpaper",
            load_tray_image(),
            f"{APP_NAME} {__version__}",
            menu=self._build_menu(),
        )
        if self.config.interval_hours > 0:
            self.scheduler.start(self.config.interval_hours, self._scheduled_update)

        if recently_updated(self.config):
            logger.info("Skipping startup update; last update was recent")
            if self.config.last_title:
                self._set_tooltip(f"{APP_NAME} — {self.config.last_title}")
        else:
            threading.Thread(
                target=self._update_now,
                kwargs={"silent_start": True},
                name="nasa-initial-update",
                daemon=True,
            ).start()

        if not has_personal_api_key(self.config):
            threading.Timer(2.0, self._remind_api_key).start()

        if self.config.auto_check_updates:
            threading.Timer(8.0, lambda: self._check_app_updates(silent=True)).start()

        logger.info("Tray started")
        self.icon.run()

    def _remind_api_key(self) -> None:
        self._notify(
            APP_NAME,
            "Get a free NASA API key in Settings (api.nasa.gov). DEMO_KEY is very limited.",
        )

    def _notify(self, title: str, message: str) -> None:
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception:  # noqa: BLE001
                logger.debug("Notification unavailable", exc_info=True)

    def _set_tooltip(self, text: str) -> None:
        if self.icon:
            self.icon.title = text[:120]

    def _refresh_menu(self) -> None:
        if self.icon:
            self.icon.menu = self._build_menu()
            try:
                self.icon.update_menu()
            except Exception:  # noqa: BLE001
                pass

    def _key_status_label(self) -> str:
        if has_personal_api_key(self.config):
            return "API key: personal"
        return "API key: DEMO (get free key)"

    def _build_menu(self) -> pystray.Menu:
        last = self.config.last_title or "None yet"
        if self.config.last_date:
            last = f"{self.config.last_date}: {last}"

        def mode_checked(mode: str):
            return lambda item: self.config.mode == mode

        def interval_checked(hours: int):
            return lambda item: self.config.interval_hours == hours

        interval_items = [
            Item(
                "Off" if hours == 0 else f"Every {hours}h",
                self._make_interval_handler(hours),
                checked=interval_checked(hours),
                radio=True,
            )
            for hours in INTERVAL_CHOICES
        ]

        return pystray.Menu(
            Item(f"Last: {last[:48]}", None, enabled=False),
            Item(self._key_status_label(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            Item("Update Now", self._on_update_now),
            Item(
                "Mode",
                pystray.Menu(
                    Item(
                        "Latest NASA photos",
                        self._make_mode_handler("latest"),
                        checked=mode_checked("latest"),
                        radio=True,
                    ),
                    Item(
                        "Random from archive",
                        self._make_mode_handler("random"),
                        checked=mode_checked("random"),
                        radio=True,
                    ),
                ),
            ),
            Item("Auto-update", pystray.Menu(*interval_items)),
            pystray.Menu.SEPARATOR,
            Item("Open images folder", self._on_open_folder),
            Item(
                "Open current wallpaper",
                self._on_open_current,
                enabled=bool(self.config.last_image_path),
            ),
            Item(
                "Run at startup",
                self._on_toggle_startup,
                checked=lambda item: is_startup_enabled(),
            ),
            Item("Get free API key…", self._on_get_api_key),
            Item("Settings…", self._on_settings),
            pystray.Menu.SEPARATOR,
            Item(
                "App updates",
                pystray.Menu(
                    Item("Check for updates", self._on_check_updates),
                    Item(
                        "Download & install update",
                        self._on_install_update,
                        enabled=self._pending_app_update is not None
                        and current_install_path() is not None,
                    ),
                    Item("Open releases page", lambda icon, item: open_url(RELEASES_PAGE)),
                    Item(
                        "Auto-check on startup",
                        self._on_toggle_auto_check,
                        checked=lambda item: self.config.auto_check_updates,
                    ),
                ),
            ),
            Item(f"Version {__version__}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            Item("Quit", self._on_quit),
        )

    def _make_mode_handler(self, mode: str):
        def handler(icon, item):  # noqa: ARG001
            self.config.mode = mode
            save_config(self.config)
            self.service.refresh_config(self.config)
            self._refresh_menu()
            self._notify(APP_NAME, f"Mode: {mode}")

        return handler

    def _make_interval_handler(self, hours: int):
        def handler(icon, item):  # noqa: ARG001
            self.config.interval_hours = hours
            save_config(self.config)
            if hours > 0:
                self.scheduler.start(hours, self._scheduled_update)
            else:
                self.scheduler.stop(join=False)
            self._refresh_menu()
            label = "off" if hours == 0 else f"every {hours}h"
            self._notify(APP_NAME, f"Auto-update {label}")

        return handler

    def _on_update_now(self, icon=None, item=None):  # noqa: ARG002
        threading.Thread(target=self._update_now, name="nasa-manual-update", daemon=True).start()

    def _scheduled_update(self) -> None:
        self._update_now(silent_start=True)

    def _update_now(self, silent_start: bool = False) -> None:
        with self._busy_lock:
            if self._busy:
                return
            self._busy = True
        try:
            if not silent_start:
                self._set_tooltip(f"{APP_NAME} — updating…")
            result = self.service.update()
            self._handle_result(result)
        finally:
            with self._busy_lock:
                self._busy = False
            self._refresh_menu()

    def _handle_result(self, result: UpdateResult) -> None:
        if result.ok:
            self._set_tooltip(f"{APP_NAME} — {result.title}")
            self._notify(APP_NAME, result.message)
            logger.info("Update ok: %s", result.message)
        else:
            self._set_tooltip(f"{APP_NAME} — {result.message}")
            self._notify(APP_NAME, result.message)
            logger.warning("Update failed: %s", result.message)
            if "rate limit" in result.message.lower() or "429" in result.message:
                self._notify(APP_NAME, "Open Settings → get a free personal API key at api.nasa.gov")

    def _on_open_folder(self, icon=None, item=None):  # noqa: ARG002
        try:
            self.cache.open_folder()
        except OSError as exc:
            self._notify(APP_NAME, str(exc))

    def _on_open_current(self, icon=None, item=None):  # noqa: ARG002
        path = self.config.last_image_path
        if path and Path(path).exists():
            try:
                open_path(path)
            except OSError as exc:
                self._notify(APP_NAME, str(exc))
        else:
            self._notify(APP_NAME, "No wallpaper file found yet.")

    def _on_toggle_startup(self, icon=None, item=None):  # noqa: ARG002
        enabled = toggle_startup()
        self._refresh_menu()
        self._notify(APP_NAME, "Startup enabled" if enabled else "Startup disabled")

    def _on_get_api_key(self, icon=None, item=None):  # noqa: ARG002
        open_url(NASA_API_SIGNUP_URL)
        self._notify(APP_NAME, "After signup, paste your key in Settings.")

    def _on_settings(self, icon=None, item=None):  # noqa: ARG002
        def worker() -> None:
            open_settings(self.config, on_saved=self._on_config_saved)

        threading.Thread(target=worker, name="nasa-settings", daemon=True).start()

    def _on_config_saved(self, config: AppConfig) -> None:
        self.config = config
        self.service.refresh_config(config)
        self._refresh_menu()
        self._notify(APP_NAME, "Settings saved")

    def _on_check_updates(self, icon=None, item=None):  # noqa: ARG002
        threading.Thread(
            target=self._check_app_updates,
            kwargs={"silent": False},
            name="nasa-app-update-check",
            daemon=True,
        ).start()

    def _on_toggle_auto_check(self, icon=None, item=None):  # noqa: ARG002
        self.config.auto_check_updates = not self.config.auto_check_updates
        save_config(self.config)
        self._refresh_menu()
        state = "on" if self.config.auto_check_updates else "off"
        self._notify(APP_NAME, f"Auto-check updates: {state}")

    def _on_install_update(self, icon=None, item=None):  # noqa: ARG002
        if self._pending_app_update is None:
            self._notify(APP_NAME, "No update queued. Use Check for updates first.")
            return
        if current_install_path() is None:
            open_url(self._pending_app_update.html_url)
            self._notify(APP_NAME, "Running from source — opening release page.")
            return
        threading.Thread(
            target=self._install_pending_update,
            name="nasa-app-update-install",
            daemon=True,
        ).start()

    def _check_app_updates(self, silent: bool = False) -> None:
        if self._app_update_busy:
            return
        self._app_update_busy = True
        try:
            from datetime import datetime

            self.config.last_app_update_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_config(self.config)
            update = check_for_update()
            if update is None:
                self._pending_app_update = None
                if not silent:
                    self._notify(APP_NAME, f"You're up to date (v{__version__}).")
                self._refresh_menu()
                return
            self._pending_app_update = update
            self._refresh_menu()
            self._notify(
                APP_NAME,
                f"Update v{update.version} available. Tray → App updates → Download & install.",
            )
            # Packaged builds: auto-install when user already opted into auto-check
            # and this is a silent startup check — only notify; install is explicit
            # to avoid surprising restarts.
        except Exception as exc:  # noqa: BLE001
            logger.warning("App update check failed: %s", exc)
            if not silent:
                self._notify(APP_NAME, str(exc))
        finally:
            self._app_update_busy = False

    def _install_pending_update(self) -> None:
        update = self._pending_app_update
        if update is None:
            return
        try:
            self._notify(APP_NAME, f"Downloading v{update.version}…")
            install_update(update)
            self._notify(APP_NAME, "Installing update and restarting…")
            self._on_quit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to install app update")
            self._notify(APP_NAME, f"Update failed: {exc}")

    def _on_quit(self, icon=None, item=None):  # noqa: ARG002
        self.scheduler.stop(join=False)
        if self.icon:
            self.icon.stop()
