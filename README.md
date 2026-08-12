# NASA Wallpaper

Lightweight **system-tray** app that sets curated NASA Astronomy Picture of the Day (APOD) images as your desktop wallpaper.

Works on **Windows**, **macOS**, and **Linux**. No main window — everything lives in the tray menu.

## Features

- Tray-only UI
- **Latest** mode — walks recent APODs for a high-quality photo
- **Random** mode — picks from the full archive (1995 → today)
- Quality filter (resolution, size, aspect, skip charts/videos)
- Auto-update intervals + optional run-at-startup
- Local cache under `Pictures/NASA_APOD`
- Single-instance lock
- Skips redundant startup updates if a recent wallpaper was set
- Free NASA API key guide built into Settings / tray menu

## Get a free NASA API key

NASA requires an API key. Signup is free and takes about a minute:

1. Open [https://api.nasa.gov/](https://api.nasa.gov/)
2. Submit the short form (name + email)
3. Copy the key you receive
4. In the app: tray → **Settings…** → paste the key → Save

You can also use tray → **Get free API key…**

Without a personal key the app falls back to NASA's shared `DEMO_KEY`, which is heavily rate-limited (about 30/hour and 50/day per IP). For normal use, always set your own key.

Optional: set environment variable `NASA_API_KEY` instead of storing it in Settings.

## Install (from source)

```bash
git clone https://github.com/pcbaaz/NASA-Wallpaper.git
cd NASA-Wallpaper
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m nasa_wallpaper
```

## Tray menu

- Update Now
- Mode → Latest / Random
- Auto-update → Off / 1h / 4h / 12h / 24h
- Open images folder / Open current wallpaper
- Run at startup
- Get free API key…
- Settings…
- Quit

## Platform notes

| OS | Wallpaper | Startup |
|----|-----------|---------|
| Windows | Desktop Fill via SystemParametersInfo | HKCU Run key |
| macOS | System Events (`osascript`) | LaunchAgent plist |
| Linux | gsettings / plasma / feh / nitrogen / swaybg | `~/.config/autostart` |

Linux users on tiling/Wayland setups may need `feh`, `nitrogen`, or `swaybg` installed.

## Config & logs

| Platform | Config / logs |
|----------|----------------|
| Windows | `%APPDATA%\NASA Wallpaper\` |
| macOS | `~/Library/Application Support/NASA Wallpaper/` |
| Linux | `~/.config/nasa-wallpaper/` |

Images: `~/Pictures/NASA_APOD`

## Build (Windows installer)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

Then compile `setup.iss` with Inno Setup. Do not commit built `.exe` files.

## Smoke test

```bash
python scripts/smoke_test.py
```

## License

MIT — see [LICENSE](LICENSE).

APOD images are courtesy of [NASA](https://apod.nasa.gov/) and respective authors.
