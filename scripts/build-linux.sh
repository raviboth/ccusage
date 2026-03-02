#!/usr/bin/env bash
#
# Build a standalone Linux AppImage using PyInstaller + appimagetool
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_NAME="Claude Code Usage Monitor"
APP_ID="com.ccusage"
APPDIR="$PROJECT_DIR/build/AppDir"

cd "$PROJECT_DIR"

# Activate venv
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: .venv not found. Run: python3 -m venv .venv && pip install -r requirements.txt pyinstaller"
    exit 1
fi

echo "Building PyInstaller binary..."
pyinstaller ccusage.spec --noconfirm --clean

echo "Assembling AppDir..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# Copy PyInstaller output into AppDir
cp -r "dist/Claude Code Usage Monitor/"* "$APPDIR/usr/bin/"

# Generate a 256x256 icon from the app's icon module
python3 -c "
from src.icons import render_tray_icon
img = render_tray_icon(None)
img = img.resize((256, 256))
img.save('$APPDIR/usr/share/icons/hicolor/256x256/apps/ccusage.png')
"

# Desktop file
cat > "$APPDIR/usr/share/applications/ccusage.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec=Claude Code Usage Monitor
Icon=ccusage
Categories=Utility;Monitor;
Comment=Monitor your Claude Code API usage limits
Terminal=false
StartupNotify=false
DESKTOP

# AppDir requires desktop file and icon at root
cp "$APPDIR/usr/share/applications/ccusage.desktop" "$APPDIR/ccusage.desktop"
cp "$APPDIR/usr/share/icons/hicolor/256x256/apps/ccusage.png" "$APPDIR/ccusage.png"

# AppRun script
cat > "$APPDIR/AppRun" <<'APPRUN'
#!/usr/bin/env bash
SELF="$(readlink -f "$0")"
HERE="${SELF%/*}"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH:-}"
exec "${HERE}/usr/bin/Claude Code Usage Monitor" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

# Download appimagetool if not present
ARCH="$(uname -m)"
APPIMAGETOOL="$PROJECT_DIR/build/appimagetool-${ARCH}.AppImage"
if [ ! -f "$APPIMAGETOOL" ]; then
    echo "Downloading appimagetool..."
    curl -fsSL -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
    chmod +x "$APPIMAGETOOL"
fi

echo "Building AppImage..."
mkdir -p "$PROJECT_DIR/dist"
ARCH="$ARCH" "$APPIMAGETOOL" "$APPDIR" "$PROJECT_DIR/dist/ccusage-${ARCH}.AppImage"

echo ""
echo "Build complete!"
echo "AppImage: $PROJECT_DIR/dist/ccusage-${ARCH}.AppImage"
echo ""
echo "To run: chmod +x dist/ccusage-${ARCH}.AppImage && ./dist/ccusage-${ARCH}.AppImage"
