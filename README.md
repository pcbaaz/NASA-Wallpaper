# 🌌 NASA Wallpaper

> A desktop application that automatically downloads and sets high-quality NASA Astronomy Picture of the Day (APOD) as your Windows wallpaper.

## ✨ Features

- 🖼️ Downloads high-quality HD images (≥1 MB)
- 🔄 Auto-updates every 4 hours
- 🚀 Runs on Windows startup
- 🖥️ System tray support
- 📂 Saves images to `Pictures/NASA_APOD`
- 🗑️ Cache management (keeps last 5 images)
- 🎨 Professional dark theme UI

## 📥 Installation

Download the latest `NASA_Wallpaper_Setup.exe` from [Releases](https://github.com/YOUR_USERNAME/NASA-Wallpaper/releases) and run it.

## 🛠️ Build from Source

```bash
# Install dependencies
pip install -r requirements.txt

# Build the EXE
pyinstaller --onedir --windowed --icon=icon.ico --add-data "icon.ico;." --name "NASA_Wallpaper" Nasa_wallpaper.py