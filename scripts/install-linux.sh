#!/usr/bin/env bash
#
# install-linux.sh -- Install Claude Code Usage Monitor as a systemd user service
#                     and create a convenience shell command.
#
set -euo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
SERVICE_NAME="ccusage.service"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_PATH="$SERVICE_DIR/$SERVICE_NAME"
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

if ! command -v systemctl &>/dev/null; then
    echo "Error: systemctl not found. This script requires systemd."
    exit 1
fi

# ---------------------------------------------------------------------------
# 1. Create systemd user service
# ---------------------------------------------------------------------------
mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_PATH" <<UNIT
[Unit]
Description=Claude Code Usage Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${VENV_PYTHON} -m src.main
WorkingDirectory=${PROJECT_DIR}
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
UNIT

echo "Systemd service written to $SERVICE_PATH"

# Reload, enable, and start
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user start "$SERVICE_NAME"
echo "Service enabled and started."

# ---------------------------------------------------------------------------
# 2. Create shell command symlink
# ---------------------------------------------------------------------------
mkdir -p "$SYMLINK_DIR"
ln -sf "$SCRIPT_DIR/claude-monitor" "$SYMLINK_PATH"
echo "Symlink created: $SYMLINK_PATH -> $SCRIPT_DIR/claude-monitor"

if [[ ":$PATH:" != *":$SYMLINK_DIR:"* ]]; then
    echo ""
    echo "NOTE: $SYMLINK_DIR is not in your PATH."
    echo "Add it by appending the following to your shell profile (~/.bashrc or ~/.zshrc):"
    echo ""
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo "Installation complete. Claude Code Usage Monitor will start automatically at login."
echo "Manual control:  claude-monitor start | stop | status"
echo "Service logs:    journalctl --user -u $SERVICE_NAME -f"
