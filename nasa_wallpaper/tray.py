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
    load_config,
    recently_updated,
    save_config,
)
from nasa_wallpaper.platform_util import (
    APOD_HOME_URL,
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

        if self.config.auto_check_updates:
            threading.Timer(8.0, lambda: self._check_app_updates(silent=True)).start()

        logger.info("Tray started")
        self.icon.run()

    def _notify(self, title: str, message: str) -> None:
        # Desktop notifications are intentionally disabled.
        logger.info("notify suppressed: %s — %s", title, message)

    def _set_tooltip(self, text: str) -> None:
        if self.icon:
            self.icon.title = text[:120]

    def _refresh_menu(self) -> None:
        # #region agent log
        try:
            import json as _json, time as _time
            from pathlib import Path as _P
            _P(r"C:\Users\behna\Projects\NASA-Wallpaper\debug-0a6770.log").open("a", encoding="utf-8").write(
                _json.dumps({"sessionId":"0a6770","hypothesisId":"B","location":"tray.py:_refresh_menu","message":"refresh menu","data":{"thread":threading.current_thread().name,"pending":None if self._pending_app_update is None else self._pending_app_update.version,"frozen":current_install_path() is not None},"timestamp":int(_time.time()*1000)}) + "\n"
            )
        except Exception:
            pass
        # #endregion
        if self.icon:
            self.icon.menu = self._build_menu()
            try:
                self.icon.update_menu()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Menu refresh failed: %s", exc)

    def _key_status_label(self) -> str:
        return "Source: apod.nasa.gov"

    def _update_status_label(self) -> str:
        if self._pending_app_update is not None:
            return f"Update available: v{self._pending_app_update.version}"
        return f"App version {__version__}"

    def _download_label(self) -> str:
        if self._pending_app_update is not None:
            return f"Download & install v{self._pending_app_update.version}"
        return "Download & install update"

    def _can_install_update(self) -> bool:
        return self._pending_app_update is not None and current_install_path() is not None

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
            Item(lambda item: self._update_status_label(), None, enabled=False),
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
            Item("Open APOD website", lambda icon, item: open_url(APOD_HOME_URL)),
            Item("Settings…", self._on_settings),
            pystray.Menu.SEPARATOR,
            Item(
                "App updates",
                pystray.Menu(
                    Item("Check & install now", self._on_check_updates),
                    Item(
                        lambda item: self._download_label(),
                        self._on_install_update,
                        # Evaluate when menu opens so a background check can enable it
                        # without relying on a successful cross-thread menu rebuild.
                        enabled=lambda item: self._can_install_update(),
                    ),
                    Item("Open releases page", lambda icon, item: open_url(RELEASES_PAGE)),
                    Item(
                        "Auto-install on startup",
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
                self._notify(APP_NAME, "Site busy — try Update Now again in a minute.")

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
            kwargs={"silent": False, "auto_install": True},
            name="nasa-app-update-check",
            daemon=True,
        ).start()

    def _on_toggle_auto_check(self, icon=None, item=None):  # noqa: ARG002
        self.config.auto_check_updates = not self.config.auto_check_updates
        save_config(self.config)
        self._refresh_menu()
        state = "on" if self.config.auto_check_updates else "off"
        self._notify(APP_NAME, f"Auto-install updates: {state}")

    def _on_install_update(self, icon=None, item=None):  # noqa: ARG002
        # #region agent log
        try:
            import json as _json, time as _time
            from pathlib import Path as _P
            _P(r"C:\Users\behna\Projects\NASA-Wallpaper\debug-0a6770.log").open("a", encoding="utf-8").write(
                _json.dumps({"sessionId":"0a6770","hypothesisId":"B","location":"tray.py:_on_install_update","message":"install clicked","data":{"pending":None if self._pending_app_update is None else self._pending_app_update.version,"install_path":str(current_install_path())},"timestamp":int(_time.time()*1000)}) + "\n"
            )
        except Exception:
            pass
        # #endregion
        if self._pending_app_update is None:
            # No queued update — run a full check + install.
            self._on_check_updates()
            return
        if current_install_path() is None:
            open_url(self._pending_app_update.html_url)
            self._set_tooltip(f"{APP_NAME} — open releases (source run)")
            self._notify(APP_NAME, "Running from source — opening release page.")
            return
        threading.Thread(
            target=self._install_pending_update,
            name="nasa-app-update-install",
            daemon=True,
        ).start()

    def _check_app_updates(self, silent: bool = False, auto_install: bool | None = None) -> None:
        if self._app_update_busy:
            return
        self._app_update_busy = True
        should_install = (
            self.config.auto_check_updates if auto_install is None else auto_install
        )
        try:
            from datetime import datetime

            self.config.last_app_update_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_config(self.config)
            update = check_for_update()
            if update is None:
                self._pending_app_update = None
                if not silent:
                    self._set_tooltip(f"{APP_NAME} — up to date (v{__version__})")
                    self._notify(APP_NAME, f"You're up to date (v{__version__}).")
                self._refresh_menu()
                return

            self._pending_app_update = update
            self._set_tooltip(f"{APP_NAME} — update v{update.version} available")
            self._refresh_menu()
            # #region agent log
            try:
                import json as _json, time as _time
                from pathlib import Path as _P
                _P(r"C:\Users\behna\Projects\NASA-Wallpaper\debug-0a6770.log").open("a", encoding="utf-8").write(
                    _json.dumps({"sessionId":"0a6770","hypothesisId":"AUTO","location":"tray.py:_check_app_updates","message":"update found","data":{"version":update.version,"should_install":should_install,"frozen":current_install_path() is not None,"silent":silent},"timestamp":int(_time.time()*1000)}) + "\n"
                )
            except Exception:
                pass
            # #endregion

            if should_install and current_install_path() is not None:
                self._set_tooltip(f"{APP_NAME} — installing v{update.version}…")
                self._notify(APP_NAME, f"Downloading and installing v{update.version}…")
                self._install_pending_update()
                return

            if not silent:
                self._notify(
                    APP_NAME,
                    f"Update v{update.version} available. Tray → App updates → Download & install.",
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("App update check failed: %s", exc)
            if not silent:
                self._set_tooltip(f"{APP_NAME} — update check failed")
                self._notify(APP_NAME, str(exc))
        finally:
            self._app_update_busy = False

    def _install_pending_update(self) -> None:
        update = self._pending_app_update
        if update is None:
            return
        try:
            self._set_tooltip(f"{APP_NAME} — downloading v{update.version}…")
            self._notify(APP_NAME, f"Downloading v{update.version}…")
            # #region agent log
            try:
                import json as _json, time as _time
                from pathlib import Path as _P
                _P(r"C:\Users\behna\Projects\NASA-Wallpaper\debug-0a6770.log").open("a", encoding="utf-8").write(
                    _json.dumps({"sessionId":"0a6770","hypothesisId":"AUTO","location":"tray.py:_install_pending_update","message":"install start","data":{"version":update.version,"path":str(current_install_path())},"timestamp":int(_time.time()*1000)}) + "\n"
                )
            except Exception:
                pass
            # #endregion
            install_update(update)
            self._notify(APP_NAME, "Installing update and restarting…")
            self._on_quit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to install app update")
            self._set_tooltip(f"{APP_NAME} — update failed")
            self._notify(APP_NAME, f"Update failed: {exc}")

    def _on_quit(self, icon=None, item=None):  # noqa: ARG002
        self.scheduler.stop(join=False)
        if self.icon:
            self.icon.stop()
