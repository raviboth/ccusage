#!/usr/bin/env bash
#
# Build a standalone macOS .app bundle using PyInstaller
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

# Activate venv
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: .venv not found. Run: python3 -m venv .venv && pip install -r requirements.txt pyinstaller"
    exit 1
fi

echo "Building Claude Usage Monitor.app..."
pyinstaller claude-usage-monitor.spec --noconfirm --clean

echo ""
echo "Build complete!"
echo "App bundle: $PROJECT_DIR/dist/Claude Usage Monitor.app"
echo ""
echo "To install, copy to /Applications:"
echo "  cp -r \"dist/Claude Usage Monitor.app\" /Applications/"
