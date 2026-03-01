import json
from dataclasses import dataclass, field

from src.constants import STATS_CACHE_PATH


@dataclass
class DailyActivity:
    date: str
    message_count: int = 0
    session_count: int = 0
    tool_call_count: int = 0


@dataclass
class LocalStats:
    daily_activity: list[DailyActivity] = field(default_factory=list)
    total_sessions: int = 0
    total_messages: int = 0
    models_used: list[str] = field(default_factory=list)
    peak_hour: int | None = None
    peak_hour_count: int = 0
    most_active_day: str | None = None
    most_active_day_messages: int = 0
    first_session_date: str | None = None


def load_local_stats() -> LocalStats | None:
    """Read and parse ~/.claude/stats-cache.json.

    Returns None if the file doesn't exist or can't be parsed.
    """
    if not STATS_CACHE_PATH.exists():
        return None

    try:
        data = json.loads(STATS_CACHE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    stats = LocalStats()

    # Daily activity
    for entry in data.get("dailyActivity", []):
        stats.daily_activity.append(
            DailyActivity(
                date=entry.get("date", ""),
                message_count=entry.get("messageCount", 0),
                session_count=entry.get("sessionCount", 0),
                tool_call_count=entry.get("toolCallCount", 0),
            )
        )

    stats.total_sessions = data.get("totalSessions", 0)
    stats.total_messages = data.get("totalMessages", 0)
    stats.first_session_date = data.get("firstSessionDate")

    # Models used
    model_usage = data.get("modelUsage", {})
    stats.models_used = list(model_usage.keys())

    # Peak hour
    hour_counts = data.get("hourCounts", {})
    if hour_counts:
        peak = max(hour_counts.items(), key=lambda x: x[1])
        stats.peak_hour = int(peak[0])
        stats.peak_hour_count = peak[1]

    # Most active day
    if stats.daily_activity:
        best = max(stats.daily_activity, key=lambda d: d.message_count)
        stats.most_active_day = best.date
        stats.most_active_day_messages = best.message_count

    return stats
