# NASA Wallpaper

[![Release](https://img.shields.io/github/v/release/pcbaaz/NASA-Wallpaper)](https://github.com/pcbaaz/NASA-Wallpaper/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)](https://github.com/pcbaaz/NASA-Wallpaper/releases/latest)

Lightweight **system-tray** app that sets curated NASA Astronomy Picture of the Day images as your desktop wallpaper.

Works on **Windows**, **macOS**, and **Linux**. Images come directly from [apod.nasa.gov](https://apod.nasa.gov/apod/) — **no API key required**.

## Download

Get the latest builds from **[Releases](https://github.com/pcbaaz/NASA-Wallpaper/releases/latest)**:

| Platform | Asset | Recommended |
|----------|--------|-------------|
| **Windows** | `NASA_Wallpaper_Setup.exe` | Yes — full installer |
| Windows portable | `NASA_Wallpaper-windows-x64.exe` | |
| macOS Apple Silicon (M1/M2/M3…) | `NASA_Wallpaper-macos-arm64` | |
| Linux x64 | `NASA_Wallpaper-linux-x64` | |

### Windows install
1. Download **NASA_Wallpaper_Setup.exe**
2. Run the setup wizard
3. A **desktop shortcut** is created by default
4. **Run at Windows startup** is enabled by default
5. Launch the app → tray icon appears
6. Choose **Mode** (Latest / Random) → **Update Now**

### First-run notes (macOS / Linux / portable)
- **macOS:** right-click the file → **Open** the first time (build is unsigned)
- **Linux:** make executable: `chmod +x NASA_Wallpaper-linux-x64`
- **Windows portable:** SmartScreen may warn on first run — More info → Run anyway

## Features

- Tray-only UI (lightweight)
- **Latest** mode — walks recent APODs for a high-quality photo
- **Random** mode — picks from the full archive (1995 → today)
- Beauty/quality filter (skips charts, montages, false-color composites, videos)
- Auto-update: Off / 1h / 4h / 12h / 24h
- Optional run-at-startup
- Local cache in `Pictures/NASA_APOD`
- Single-instance lock
- **In-app updates** from GitHub Releases
- No NASA API key / no DEMO_KEY limits

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
- Open APOD website
- Settings…
- App updates → Check & install / Auto-install on startup
- Quit

## App updates

Packaged builds **auto-download and replace themselves** when a newer GitHub Release exists (enabled by default):

1. On startup the app checks Releases
2. If newer → downloads, replaces the binary, and restarts
3. Or use Tray → **App updates → Check & install now**

You can turn auto-install off under **App updates → Auto-install on startup**.

## Platform notes

| OS | Wallpaper | Startup |
|----|-----------|---------|
| Windows | Desktop Fill (`SystemParametersInfo`) | HKCU Run key |
| macOS | System Events (`osascript`) | LaunchAgent plist |
| Linux | gsettings / Plasma / feh / nitrogen / swaybg | `~/.config/autostart` |

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

## Smoke test

```bash
python scripts/smoke_test.py
```

## License

MIT — see [LICENSE](LICENSE).

APOD images are courtesy of [NASA](https://apod.nasa.gov/) and respective authors.
