#!/bin/bash
# Windows build via Wine: PyInstaller onedir + Inno Setup installer + portable zip
# Lean release: one Windows build = installer + zip (no onefile portable exe).
set -e
export WINEPREFIX=/workspace/exwifi/.wine WINEDEBUG=-all
export PATH="/workspace/wine-portable/current/bin:$PATH"
cd "$(dirname "$0")"
V=$(grep -oP 'APP_VERSION = "\K[^"]+' fireout_online.py)
PY='C:\Python311\python.exe'
python3 test/check_glyphs.py || { echo "GLYPH CHECK FAILED"; exit 1; }
wine "$PY" -m PyInstaller --noconfirm "FIREOUT ONLINE.spec" > build_dir.log 2>&1; echo DIR_DONE
wine "C:\\InnoSetup\\ISCC.exe" installer.iss > build_iss.log 2>&1; echo ISS_DONE
cd dist && rm -f FIREOUT-ONLINE-$V-Windows-x64.zip && python3 -c "import shutil; shutil.make_archive('FIREOUT-ONLINE-$V-Windows-x64', 'zip', '.', 'FIREOUT ONLINE')" && echo ZIP_DONE
ls -la
