#!/usr/bin/env bash
#
# uninstall-linux.sh -- Remove the Claude Code Usage Monitor systemd user service
#                       and shell command symlink.
#
set -euo pipefail

SERVICE_NAME="ccusage.service"
SERVICE_PATH="$HOME/.config/systemd/user/$SERVICE_NAME"
SYMLINK_PATH="$HOME/.local/bin/claude-monitor"

# ---------------------------------------------------------------------------
# 1. Stop, disable, and remove systemd service
# ---------------------------------------------------------------------------
if [[ -f "$SERVICE_PATH" ]]; then
    systemctl --user stop "$SERVICE_NAME" 2>/dev/null || true
    systemctl --user disable "$SERVICE_NAME" 2>/dev/null || true
    rm -f "$SERVICE_PATH"
    systemctl --user daemon-reload
    echo "Systemd service stopped, disabled, and removed."
else
    echo "Systemd service file not found (already removed?)."
fi

# ---------------------------------------------------------------------------
# 2. Remove shell command symlink
# ---------------------------------------------------------------------------
if [[ -L "$SYMLINK_PATH" ]]; then
    rm -f "$SYMLINK_PATH"
    echo "Symlink removed: $SYMLINK_PATH"
else
    echo "Symlink not found at $SYMLINK_PATH (already removed?)."
fi

echo ""
echo "Uninstallation complete."
