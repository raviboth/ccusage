# Claude Code Usage Monitor

A lightweight desktop utility for macOS and Linux that displays your Claude Code usage limits in the system tray and a dashboard window.

## Features

- **System tray icon** showing your current 5-hour usage percentage as a color-coded ring (green/yellow/red)
- **Right-click menu** with all usage stats and reset times at a glance
- **Dashboard window** with progress bars, reset countdowns, daily activity charts, and usage insights
- **Configurable alerts** — set a custom 5h usage threshold (default 70%) to get notified before hitting limits
- **Reset notifications** — opt-in alerts when your usage window resets
- **Extra usage tracking** for overage credits (if enabled on your plan)
- Polls the Anthropic usage API every 60 seconds with manual refresh option
- Stores usage history locally in SQLite for trend tracking

## Requirements

- Python 3.11+
- macOS or Linux
- An active [Claude Code](https://docs.anthropic.com/en/docs/claude-code) login (the app reads your existing credentials)

## Installation

```bash
git clone https://github.com/raviboth/claude-code-usage-monitor.git
cd claude-code-usage-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Auto-Start on Login

**macOS:**
```bash
./scripts/install-macos.sh
```

**Linux:**
```bash
./scripts/install-linux.sh
```

To uninstall, run the corresponding `uninstall-macos.sh` or `uninstall-linux.sh`.

## Usage

### Manual Start

```bash
source .venv/bin/activate
python -m src.main
```

### Using the CLI Wrapper

```bash
./scripts/claude-monitor start    # Start in background
./scripts/claude-monitor stop     # Stop
./scripts/claude-monitor status   # Check if running
```

The app will appear in your system tray. Right-click the icon to see usage stats or open the dashboard.

### Tray Icon

The tray icon displays the current 5h usage percentage inside a color-coded ring:

| Color | Meaning |
|-------|---------|
| Green | 0-59% usage |
| Yellow | 60-79% usage |
| Red | 80%+ usage |

### Dashboard

The dashboard shows:
- **5-Hour Limit** — rolling usage with reset countdown
- **7-Day Limit** — weekly usage with reset countdown
- **Extra Usage** — overage credits used vs. monthly cap (if enabled)
- **Alerts** — configurable threshold for 5h usage notifications (spinbox, 10-100%) and toggle for reset notifications
- **Daily Activity** — bar chart of messages, sessions, or tool calls over the last 30 days
- **Insights** — peak hours, most active day, models used, total sessions

## How It Works

The app reads your Claude Code OAuth token from the system credential store (macOS Keychain or Linux `secret-tool`) and polls the Anthropic usage API. No API keys or tokens are stored by this app — credentials are read fresh from the keychain on each request.

Local usage history from `~/.claude/stats-cache.json` is used for the activity chart and insights.

## Security

- **No credentials stored** — OAuth tokens are read from the system keychain at runtime and held in memory only for the duration of each API call
- **No logging of sensitive data** — authorization headers are never printed, logged, or written to disk
- **Restricted file permissions** — SQLite database is created with `0600` permissions in the platform app data directory
- **Parameterized SQL** — all database queries use parameterized statements
- **HTTPS only** — all API communication uses TLS

Data is stored locally in:
- macOS: `~/Library/Application Support/claude-usage-monitor/`
- Linux: `~/.local/share/claude-usage-monitor/`

## Project Structure

```
src/
├── main.py            # Entry point, wires everything together
├── auth.py            # Token retrieval from system keychain
├── api.py             # Usage API polling
├── db.py              # SQLite storage for usage history
├── local_stats.py     # Reads ~/.claude/stats-cache.json
├── notifications.py   # Threshold and reset alert notifications
├── tray.py            # System tray icon and menu (QSystemTrayIcon)
├── dashboard.py       # Main PyQt6 window with progress bars
├── charts.py          # Daily activity chart and insights panel
├── icons.py           # Dynamic tray icon rendering with Pillow
└── constants.py       # Configuration values

scripts/
├── claude-monitor       # CLI wrapper (start/stop/status)
├── install-macos.sh     # macOS launch agent installer
├── uninstall-macos.sh   # macOS launch agent uninstaller
├── install-linux.sh     # Linux systemd service installer
└── uninstall-linux.sh   # Linux systemd service uninstaller
```

## Known Limitations

- The usage API endpoint is internal and undocumented — Anthropic could change it at any time. The app degrades gracefully if the endpoint is unavailable.
- The OAuth token is managed by Claude Code. If you're not logged in, the app will show a "not authenticated" message.
- On macOS with a notch, the tray icon may be hidden if the menu bar is crowded. Hold Cmd and drag other icons to make room.

## License

MIT
