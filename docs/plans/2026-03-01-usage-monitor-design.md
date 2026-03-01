# Claude Code Usage Monitor — Design Document

A lightweight desktop app for macOS and Linux that displays Claude Code usage limits in a system tray widget and a dashboard window.

## Problem

Claude Code shows usage limits only inside an active terminal session via `/usage`. There's no way to monitor your 5-hour and 7-day limit percentages at a glance while working outside the terminal.

## Solution

A Python desktop utility with:
- A system tray icon showing the current 5h usage percentage (color-coded)
- A right-click menu with all usage stats and reset times
- A dashboard window with progress bars, reset countdowns, daily activity charts, and usage insights

## Architecture

```
┌─────────────────────────────────────┐
│         System Tray (pystray)       │
│  Dynamic icon: "37%" color-coded    │
│  Right-click menu: stats + actions  │
├─────────────────────────────────────┤
│         Main Window (PyQt6)         │
│  Progress bars, charts, insights    │
├─────────────────────────────────────┤
│         Backend Service             │
│  Poll API (60s) + read local files  │
│  SQLite for history snapshots       │
└─────────────────────────────────────┘
```

### Components

- **pystray**: System tray icon and right-click menu (cross-platform macOS/Linux)
- **PyQt6**: Main dashboard window
- **Pillow**: Dynamic icon rendering (percentage text on colored circle)
- **pyqtgraph**: Lightweight bar charts for daily activity
- **SQLite**: Historical usage snapshots
- **Background thread**: Polls the usage API every 60 seconds

## Data Sources

### 1. Live Usage Limits (API)

The app polls an internal Anthropic endpoint every 60 seconds.

```
GET https://api.anthropic.com/api/oauth/usage
Headers:
  Authorization: Bearer <oauth_access_token>
  anthropic-beta: oauth-2025-04-20
```

Response:

```json
{
  "five_hour": { "utilization": 0.37, "resets_at": "2026-03-01T18:00:00Z" },
  "seven_day": { "utilization": 0.26, "resets_at": "2026-03-07T00:00:00Z" },
  "seven_day_opus": { "utilization": 0.08, "resets_at": null }
}
```

- `utilization` is a float from 0.0 to 1.0+ (can exceed 1.0 when over-limit)
- No confirmed rate limits on this endpoint; 60s polling matches community consensus
- A manual "Refresh Now" option triggers an immediate poll

### 2. Historical Activity (Local Files)

Read from `~/.claude/stats-cache.json` at startup. This file is maintained by Claude Code and contains pre-computed daily activity: message counts, session counts, tool call counts, and token usage by model. Used for the daily activity chart and insights section.

### 3. SQLite Storage

Located in the platform-appropriate app data directory (never in the project repo):
- macOS: `~/Library/Application Support/claude-usage-monitor/`
- Linux: `~/.local/share/claude-usage-monitor/`

Schema:

```sql
CREATE TABLE usage_snapshots (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    five_hour_util REAL,
    five_hour_resets_at TEXT,
    seven_day_util REAL,
    seven_day_resets_at TEXT,
    seven_day_opus_util REAL
);
```

A row is inserted every poll cycle. Rows older than 30 days are pruned automatically.

## Token Management

The OAuth access token is read from the system credential store at runtime:
- **macOS**: `security find-generic-password -s "Claude Code-credentials" -w`
- **Linux**: `secret-tool` or equivalent credential store lookup

The token JSON blob contains an `access_token` field (starts with `sk-ant-oat01-...`). It is held in memory only for the duration of the API call, then dereferenced.

## System Tray

### Dynamic Icon

- Rendered with Pillow: white/light text on a colored circle
- Size: 22x22px (macOS), 24x24px (Linux)
- Shows the rounded 5h percentage as text, e.g. "37" (no percent sign — too small)
- Color thresholds:
  - Green (#4CAF50): 0-59%
  - Yellow (#FF9800): 60-79%
  - Red (#F44336): 80%+
- Re-rendered on every poll

### Right-Click Menu

```
5h: 37% · resets in 2h 14m
7d: 26% · resets in 3d 8h
Opus 7d: 8% · no reset scheduled
─────────────────
Open Dashboard
Refresh Now
─────────────────
Quit
```

- Top 3 items are display-only (greyed out)
- Menu rebuilds on every poll with fresh values

### Edge Cases

- **Token missing/expired**: Icon shows "?" in grey. Menu shows "Not authenticated — run Claude Code to log in"
- **API error/timeout**: Keep showing last known values with "(stale)" suffix
- **Utilization > 100%**: Icon turns red, shows "100+"

## Main Dashboard Window

Single scrollable window, ~400x600px default, resizable.

```
┌──────────────────────────────────────┐
│  Claude Code Usage Monitor     [—][x]│
├──────────────────────────────────────┤
│                                      │
│  5-Hour Limit                        │
│  [████████████░░░░░░░░] 37%          │
│  Resets in 2h 14m · 5:45 PM today    │
│                                      │
│  7-Day Limit                         │
│  [██████░░░░░░░░░░░░░░] 26%          │
│  Resets in 3d 8h · Mar 4 at 6:00 PM  │
│                                      │
│  7-Day Opus                          │
│  [██░░░░░░░░░░░░░░░░░░] 8%           │
│  No reset scheduled                  │
│                                      │
│  Last updated: 12 seconds ago  [↻]   │
│                                      │
├──────────────────────────────────────┤
│  Daily Activity (last 30 days)       │
│                                      │
│  ▐█                                  │
│  ▐█ ▐▌    ▐█                         │
│  ▐█ ▐▌ ▐▌ ▐█ ▐▌                      │
│  ▐█ ▐▌ ▐▌ ▐█ ▐▌ ▐▌    ▐▌            │
│  ─────────────────────────           │
│  Jan 28  Feb 5  Feb 12  Feb 28       │
│                                      │
│  [Messages ▼]  Total: 5,344          │
│                                      │
├──────────────────────────────────────┤
│  Insights                            │
│  Peak hour: 4 PM (7 sessions)        │
│  Total sessions: 36                  │
│  Most active day: Feb 10 (936 msgs)  │
│  Models: Opus 4.6, Opus 4.5          │
└──────────────────────────────────────┘
```

- Progress bars use the same green/yellow/red color scheme as the tray icon
- "Resets in" shows both relative and absolute time
- Chart uses `pyqtgraph` (lightweight, no matplotlib)
- Dropdown toggles chart between Messages, Tokens, and Sessions
- Insights computed from `stats-cache.json` at startup
- Window hides (not closes) on X — stays in tray. Cmd+Q / tray Quit exits the app

## Security

**Principle: The app never stores, logs, or writes credentials to disk.**

### Token handling

- Read from system keychain at runtime only
- Held in memory for the duration of the API call, then dereferenced
- Never written to SQLite, config files, log files, or any other persistent storage

### What gets committed to GitHub

- Source code only
- `.gitignore` includes: `*.db`, `*.sqlite`, `__pycache__/`, `.env`, `*.log`
- No config files with user-specific paths or secrets

### What stays local

- SQLite database in platform app data directory
- No log files by default

### Code-level safeguards

- API call function takes the token as a parameter, not a global
- HTTP request helper strips `Authorization` from error messages and tracebacks
- No `print()` or `logging.debug()` of request headers
- `.gitignore` is generated as part of project setup

## Dependencies

```
pystray          # System tray
PyQt6            # Dashboard window
Pillow           # Dynamic icon rendering
pyqtgraph        # Charts
requests         # HTTP client
```

## Platform Support

- **macOS**: Full support. Keychain for credentials, `~/Library/Application Support/` for data.
- **Linux**: Full support. `secret-tool` for credentials, `~/.local/share/` for data. Requires a system tray compatible desktop environment.

## Known Limitations

- The `/api/oauth/usage` endpoint is internal and undocumented. Anthropic could change or remove it at any time. If that happens, the app degrades gracefully — shows "?" and relies on local history data only.
- The OAuth token is managed by Claude Code. If the user isn't logged into Claude Code, the app can't authenticate.
- `stats-cache.json` is only updated when Claude Code computes it. Historical data may lag behind actual usage.

## File Structure

```
claude-code-usage-monitor/
├── docs/plans/
│   └── 2026-03-01-usage-monitor-design.md
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point, starts tray + Qt app
│   ├── api.py               # Usage API polling
│   ├── auth.py              # Token retrieval from system keychain
│   ├── db.py                # SQLite operations
│   ├── tray.py              # System tray icon + menu
│   ├── dashboard.py         # Main Qt window
│   ├── charts.py            # pyqtgraph chart widgets
│   ├── icons.py             # Dynamic icon rendering with Pillow
│   ├── local_stats.py       # Read ~/.claude/stats-cache.json
│   └── constants.py         # Colors, thresholds, intervals
├── .gitignore
├── requirements.txt
└── README.md
```
