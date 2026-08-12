# Build Windows portable EXE + Inno Setup installer.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\build.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Installing dependencies..."
python -m pip install -r requirements.txt

Write-Host "Cleaning previous build..."
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path installer | Out-Null

Write-Host "Running PyInstaller (onefile)..."
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

$iscc = @(
  "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe",
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
  "C:\Program Files\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($iscc) {
  Write-Host "Compiling installer with Inno Setup..."
  & $iscc setup.iss
  Write-Host "Installer: installer\NASA_Wallpaper_Setup.exe"
} else {
  Write-Host "Inno Setup not found — portable only: dist\NASA_Wallpaper.exe"
  Write-Host "Install Inno Setup 6 to build NASA_Wallpaper_Setup.exe"
}

Write-Host "Portable: dist\NASA_Wallpaper.exe"
