import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.api import UsageData
from src.constants import APP_DATA_DIR, DB_FILENAME, DB_PRUNE_DAYS

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS usage_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    five_hour_util REAL,
    five_hour_resets_at TEXT,
    seven_day_util REAL,
    seven_day_resets_at TEXT,
    seven_day_opus_util REAL,
    extra_usage_util REAL,
    extra_usage_used REAL,
    extra_usage_limit REAL
);
"""

_INSERT = """
INSERT INTO usage_snapshots
    (timestamp, five_hour_util, five_hour_resets_at,
     seven_day_util, seven_day_resets_at, seven_day_opus_util,
     extra_usage_util, extra_usage_used, extra_usage_limit)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

_PRUNE = """
DELETE FROM usage_snapshots WHERE timestamp < ?;
"""

_SELECT_RECENT = """
SELECT timestamp, five_hour_util, seven_day_util, seven_day_opus_util
FROM usage_snapshots
WHERE timestamp >= ?
ORDER BY timestamp ASC;
"""


class UsageDB:
    def __init__(self) -> None:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        db_path = APP_DATA_DIR / DB_FILENAME
        if not db_path.exists():
            db_path.touch(mode=0o600)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def insert_snapshot(self, data: UsageData) -> None:
        with self._lock:
            self._conn.execute(
                _INSERT,
                (
                    data.fetched_at.isoformat(),
                    data.five_hour.utilization,
                    data.five_hour.resets_at.isoformat() if data.five_hour.resets_at else None,
                    data.seven_day.utilization,
                    data.seven_day.resets_at.isoformat() if data.seven_day.resets_at else None,
                    data.seven_day_opus.utilization if data.seven_day_opus else None,
                    data.extra_usage.utilization if data.extra_usage else None,
                    data.extra_usage.used_credits if data.extra_usage else None,
                    data.extra_usage.monthly_limit if data.extra_usage else None,
                ),
            )
            self._conn.commit()

    def prune_old(self) -> None:
        with self._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(days=DB_PRUNE_DAYS)
            self._conn.execute(_PRUNE, (cutoff.isoformat(),))
            self._conn.commit()

    def get_recent(self, days: int = 7) -> list[dict]:
        with self._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            rows = self._conn.execute(_SELECT_RECENT, (cutoff.isoformat(),)).fetchall()
        return [
            {
                "timestamp": row[0],
                "five_hour_util": row[1],
                "seven_day_util": row[2],
                "seven_day_opus_util": row[3],
            }
            for row in rows
        ]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
