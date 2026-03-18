import sys
from pathlib import Path

# API
USAGE_API_URL = "https://api.anthropic.com/api/oauth/usage"
USAGE_API_BETA_HEADER = "oauth-2025-04-20"
POLL_INTERVAL_SECONDS = 300
API_TIMEOUT_SECONDS = 5

# Keychain
KEYCHAIN_SERVICE_NAME = "Claude Code-credentials"

# Colors (hex)
COLOR_GREEN = "#4CAF50"
COLOR_YELLOW = "#FF9800"
COLOR_RED = "#F44336"
COLOR_GREY = "#9E9E9E"

# Usage thresholds (utilization float 0.0-1.0)
THRESHOLD_YELLOW = 0.60
THRESHOLD_RED = 0.80

# Dashboard
WINDOW_DEFAULT_WIDTH = 400
WINDOW_DEFAULT_HEIGHT = 600
WINDOW_TITLE = "Claude Code Usage Monitor"

# Database
DB_FILENAME = "usage_history.db"
DB_PRUNE_DAYS = 30

# Local stats
STATS_CACHE_PATH = Path.home() / ".claude" / "stats-cache.json"

# App data directory
if sys.platform == "darwin":
    APP_DATA_DIR = Path.home() / "Library" / "Application Support" / "ccusage"
else:
    APP_DATA_DIR = Path.home() / ".local" / "share" / "ccusage"
