# Build NASA Wallpaper with PyInstaller (onefile, Windows).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\build.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Installing dependencies..."
python -m pip install -r requirements.txt

Write-Host "Cleaning previous build..."
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue

Write-Host "Running PyInstaller..."
python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name NASA_Wallpaper `
  --icon assets\icon.ico `
  --add-data "assets\icon.ico;assets" `
  --add-data "assets\icon.png;assets" `
  --hidden-import pystray._win32 `
  run.py

Write-Host ""
Write-Host "Build complete: dist\NASA_Wallpaper.exe"
Write-Host "GitHub Actions builds Windows/macOS/Linux releases on version tags (v*)."
