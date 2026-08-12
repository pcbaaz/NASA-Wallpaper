#!/usr/bin/env bash
# Build NASA Wallpaper with PyInstaller (macOS / Linux).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m pip install -r requirements.txt

rm -rf dist build

ADD_DATA="assets/icon.ico:assets"
ADD_DATA_PNG="assets/icon.png:assets"
EXTRA=()
if [[ "$(uname -s)" == "Darwin" ]]; then
  EXTRA+=(--windowed --icon assets/icon.png --hidden-import pystray._darwin)
else
  EXTRA+=(--noconsole)
fi

python3 -m PyInstaller \
  --noconfirm --clean --onefile \
  --name NASA_Wallpaper \
  --add-data "$ADD_DATA" \
  --add-data "$ADD_DATA_PNG" \
  "${EXTRA[@]}" \
  run.py

echo "Build complete: dist/NASA_Wallpaper"
