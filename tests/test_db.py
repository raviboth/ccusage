"""Tests for src/db.py — UsageDB insert, prune, and lifecycle."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.api import ExtraUsage, UsageData, UsageWindow
from src.db import UsageDB


def _make_usage_data(fetched_at=None, five_hour_util=0.5):
    return UsageData(
        five_hour=UsageWindow(utilization=five_hour_util, resets_at=None),
        seven_day=UsageWindow(utilization=0.1, resets_at=None),
        seven_day_opus=None,
        extra_usage=None,
        fetched_at=fetched_at or datetime.now(timezone.utc),
    )


@pytest.fixture
def db(tmp_path):
    with patch("src.db.APP_DATA_DIR", tmp_path):
        database = UsageDB()
        yield database
        database.close()


class TestUsageDB:
    def test_insert_and_schema(self, db):
        data = _make_usage_data()
        db.insert_snapshot(data)
        # Verify row exists
        cursor = db._conn.execute("SELECT COUNT(*) FROM usage_snapshots")
        assert cursor.fetchone()[0] == 1

    def test_multiple_inserts(self, db):
        for i in range(5):
            db.insert_snapshot(_make_usage_data(five_hour_util=i * 0.1))
        cursor = db._conn.execute("SELECT COUNT(*) FROM usage_snapshots")
        assert cursor.fetchone()[0] == 5

    def test_insert_with_all_fields(self, db):
        data = UsageData(
            five_hour=UsageWindow(
                utilization=0.42,
                resets_at=datetime(2026, 3, 19, 12, 0, tzinfo=timezone.utc),
            ),
            seven_day=UsageWindow(utilization=0.10, resets_at=None),
            seven_day_opus=UsageWindow(utilization=0.05, resets_at=None),
            extra_usage=ExtraUsage(
                is_enabled=True,
                monthly_limit=50.0,
                used_credits=12.34,
                utilization=0.25,
            ),
            fetched_at=datetime.now(timezone.utc),
        )
        db.insert_snapshot(data)
        row = db._conn.execute("SELECT * FROM usage_snapshots").fetchone()
        assert row is not None
        # five_hour_util is column index 2
        assert row[2] == pytest.approx(0.42)
        # seven_day_opus_util is column index 6
        assert row[6] == pytest.approx(0.05)
        # extra_usage_util is column index 7
        assert row[7] == pytest.approx(0.25)

    def test_prune_removes_old(self, db):
        old = datetime.now(timezone.utc) - timedelta(days=60)
        db.insert_snapshot(_make_usage_data(fetched_at=old))
        db.insert_snapshot(_make_usage_data())  # recent
        db.prune_old()
        cursor = db._conn.execute("SELECT COUNT(*) FROM usage_snapshots")
        assert cursor.fetchone()[0] == 1

    def test_prune_keeps_recent(self, db):
        recent = datetime.now(timezone.utc) - timedelta(days=5)
        db.insert_snapshot(_make_usage_data(fetched_at=recent))
        db.prune_old()
        cursor = db._conn.execute("SELECT COUNT(*) FROM usage_snapshots")
        assert cursor.fetchone()[0] == 1

    def test_close_and_insert_noop(self, db):
        db.close()
        # Should not raise
        db.insert_snapshot(_make_usage_data())

    def test_context_manager(self, tmp_path):
        with patch("src.db.APP_DATA_DIR", tmp_path):
            with UsageDB() as database:
                database.insert_snapshot(_make_usage_data())
            # After exit, connection is closed
            assert database._conn is None
