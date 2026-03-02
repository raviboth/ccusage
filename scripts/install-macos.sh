#!/usr/bin/env bash
#
# install-macos.sh -- Install Claude Code Usage Monitor as a macOS Launch Agent
#                     and create a convenience shell command.
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
PLIST_NAME="com.ccusage.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"
SYMLINK_DIR="$HOME/.local/bin"
SYMLINK_PATH="$SYMLINK_DIR/claude-monitor"

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Error: Virtual environment not found at $VENV_PYTHON"
    echo "Create one first:  python3 -m venv $PROJECT_DIR/.venv && $VENV_PYTHON -m pip install -r $PROJECT_DIR/requirements.txt"
    exit 1
fi

# ---------------------------------------------------------------------------
# 1. Install Launch Agent
# ---------------------------------------------------------------------------
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ccusage</string>

    <key>ProgramArguments</key>
    <array>
        <string>${VENV_PYTHON}</string>
        <string>-m</string>
        <string>src.main</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>${PROJECT_DIR}/claude-monitor.log</string>

    <key>StandardErrorPath</key>
    <string>${PROJECT_DIR}/claude-monitor.log</string>
</dict>
</plist>
PLIST

echo "Launch Agent plist written to $PLIST_PATH"

# Load the agent (unload first if it was already loaded)
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"
echo "Launch Agent loaded."

# ---------------------------------------------------------------------------
# 2. Create shell command symlink
# ---------------------------------------------------------------------------
mkdir -p "$SYMLINK_DIR"
ln -sf "$SCRIPT_DIR/claude-monitor" "$SYMLINK_PATH"
echo "Symlink created: $SYMLINK_PATH -> $SCRIPT_DIR/claude-monitor"

# Remind user to add ~/.local/bin to PATH if needed
if [[ ":$PATH:" != *":$SYMLINK_DIR:"* ]]; then
    echo ""
    echo "NOTE: $SYMLINK_DIR is not in your PATH."
    echo "Add it by appending the following to your shell profile (~/.zshrc or ~/.bashrc):"
    echo ""
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo "Installation complete. Claude Code Usage Monitor will start automatically at login."
echo "Manual control:  claude-monitor start | stop | status"
