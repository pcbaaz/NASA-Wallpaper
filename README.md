# NASA Wallpaper

[![Release](https://img.shields.io/github/v/release/pcbaaz/NASA-Wallpaper)](https://github.com/pcbaaz/NASA-Wallpaper/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)](https://github.com/pcbaaz/NASA-Wallpaper/releases/latest)

Lightweight **system-tray** app that sets curated NASA Astronomy Picture of the Day (APOD) images as your desktop wallpaper.

Works on **Windows**, **macOS**, and **Linux**. No main window — everything lives in the tray menu.

## Download

Get the latest binaries from **[Releases](https://github.com/pcbaaz/NASA-Wallpaper/releases/latest)**:

| Platform | Asset |
|----------|--------|
| Windows x64 | `NASA_Wallpaper-windows-x64.exe` |
| macOS Apple Silicon (M1/M2/M3…) | `NASA_Wallpaper-macos-arm64` |
| macOS Intel | `NASA_Wallpaper-macos-x64` |
| Linux x64 | `NASA_Wallpaper-linux-x64` |

After download:
1. Run the app (a tray icon appears near the clock)
2. Tray → **Get free API key…** (opens [api.nasa.gov](https://api.nasa.gov/))
3. Tray → **Settings…** → paste your key → Save
4. Choose **Mode** (Latest / Random) and press **Update Now**

### First-run notes
- **macOS:** right-click the file → **Open** the first time (build is unsigned)
- **Linux:** make executable: `chmod +x NASA_Wallpaper-linux-x64`
- **Windows:** SmartScreen may warn on first run — choose More info → Run anyway

## Features

- Tray-only UI (lightweight)
- **Latest** mode — walks recent APODs for a high-quality photo
- **Random** mode — picks from the full archive (1995 → today)
- Quality filter (resolution, size, aspect ratio; skips charts/videos)
- Auto-update: Off / 1h / 4h / 12h / 24h
- Optional run-at-startup
- Local cache in `Pictures/NASA_APOD`
- Single-instance lock
- Built-in free NASA API key guide

## Get a free NASA API key

Signup is free and takes about a minute:

1. Open [https://api.nasa.gov/](https://api.nasa.gov/)
2. Submit the short form (name + email)
3. Copy the key you receive
4. In the app: tray → **Settings…** → paste → Save

Without a personal key the app falls back to NASA's shared `DEMO_KEY` (about **30/hour** and **50/day** per IP). For normal use, set your own key.

Optional: set environment variable `NASA_API_KEY`.

## Install from source

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
| Windows | Desktop Fill (`SystemParametersInfo`) | HKCU Run key |
| macOS | System Events (`osascript`) | LaunchAgent plist |
| Linux | gsettings / Plasma / feh / nitrogen / swaybg | `~/.config/autostart` |

Linux Wayland/tiling users may need `feh`, `nitrogen`, or `swaybg`.

## Config & logs

| Platform | Config / logs |
|----------|----------------|
| Windows | `%APPDATA%\NASA Wallpaper\` |
| macOS | `~/Library/Application Support/NASA Wallpaper/` |
| Linux | `~/.config/nasa-wallpaper/` |

Images: `~/Pictures/NASA_APOD`

## Build locally

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

```bash
# macOS / Linux
bash scripts/build.sh
```

Official multi-platform releases are produced by GitHub Actions when a `v*` tag is pushed.

## Smoke test

```bash
python scripts/smoke_test.py
```

## License

MIT — see [LICENSE](LICENSE).

APOD images are courtesy of [NASA](https://apod.nasa.gov/) and respective authors.
