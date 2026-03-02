#!/usr/bin/env bash
#
# Build a standalone Linux AppImage using PyInstaller + appimagetool
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_NAME="Claude Usage Monitor"
APP_ID="com.claude-usage-monitor"
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
pyinstaller claude-usage-monitor.spec --noconfirm --clean

echo "Assembling AppDir..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# Copy PyInstaller output into AppDir
cp -r "dist/Claude Usage Monitor/"* "$APPDIR/usr/bin/"

# Generate a 256x256 icon from the app's icon module
python3 -c "
from src.icons import render_tray_icon
img = render_tray_icon(None)
img = img.resize((256, 256))
img.save('$APPDIR/usr/share/icons/hicolor/256x256/apps/claude-usage-monitor.png')
"

# Desktop file
cat > "$APPDIR/usr/share/applications/claude-usage-monitor.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=$APP_NAME
Exec=Claude Usage Monitor
Icon=claude-usage-monitor
Categories=Utility;Monitor;
Comment=Monitor your Claude Code API usage limits
Terminal=false
StartupNotify=false
DESKTOP

# AppDir requires desktop file and icon at root
cp "$APPDIR/usr/share/applications/claude-usage-monitor.desktop" "$APPDIR/claude-usage-monitor.desktop"
cp "$APPDIR/usr/share/icons/hicolor/256x256/apps/claude-usage-monitor.png" "$APPDIR/claude-usage-monitor.png"

# AppRun script
cat > "$APPDIR/AppRun" <<'APPRUN'
#!/usr/bin/env bash
SELF="$(readlink -f "$0")"
HERE="${SELF%/*}"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH:-}"
exec "${HERE}/usr/bin/Claude Usage Monitor" "$@"
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
ARCH="$ARCH" "$APPIMAGETOOL" "$APPDIR" "$PROJECT_DIR/dist/Claude_Usage_Monitor-${ARCH}.AppImage"

echo ""
echo "Build complete!"
echo "AppImage: $PROJECT_DIR/dist/Claude_Usage_Monitor-${ARCH}.AppImage"
echo ""
echo "To run: chmod +x dist/Claude_Usage_Monitor-${ARCH}.AppImage && ./dist/Claude_Usage_Monitor-${ARCH}.AppImage"
