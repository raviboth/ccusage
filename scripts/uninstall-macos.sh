#!/usr/bin/env bash
#
# uninstall-macos.sh -- Remove the Claude Code Usage Monitor Launch Agent
#                       and shell command symlink.
#
set -euo pipefail

PLIST_NAME="com.ccusage.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"
SYMLINK_PATH="$HOME/.local/bin/claude-monitor"

# ---------------------------------------------------------------------------
# 1. Unload and remove Launch Agent
# ---------------------------------------------------------------------------
if [[ -f "$PLIST_PATH" ]]; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm -f "$PLIST_PATH"
    echo "Launch Agent unloaded and plist removed."
else
    echo "Launch Agent plist not found (already removed?)."
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
