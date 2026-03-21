"""Tests for src/notifications.py — threshold and reset alerts."""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.api import UsageData, UsageWindow
from src.notifications import NotificationManager


def _make_usage_data(utilization=0.5, resets_at=None, seven_day_util=0.1, seven_day_resets_at=None):
    """Create a minimal UsageData for testing."""
    return UsageData(
        five_hour=UsageWindow(utilization=utilization, resets_at=resets_at),
        seven_day=UsageWindow(utilization=seven_day_util, resets_at=seven_day_resets_at),
        seven_day_opus=None,
        extra_usage=None,
        fetched_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mgr(tmp_path):
    """Create a NotificationManager with a temp settings dir."""
    with patch("src.notifications.SETTINGS_FILE", tmp_path / "settings.json"):
        with patch("src.notifications.APP_DATA_DIR", tmp_path):
            m = NotificationManager()
            yield m


# ── Threshold alerts ─────────────────────────────────────────────────────────


class TestThresholdAlerts:
    @patch("src.notifications.notification.notify")
    def test_fires_when_crossing(self, mock_notify, mgr):
        data = _make_usage_data(utilization=0.75)
        mgr.check(data)
        mock_notify.assert_called_once()
        assert "75%" in mock_notify.call_args[1]["message"]

    @patch("src.notifications.notification.notify")
    def test_no_duplicate(self, mock_notify, mgr):
        data = _make_usage_data(utilization=0.75)
        mgr.check(data)
        mgr.check(data)
        assert mock_notify.call_count == 1

    @patch("src.notifications.notification.notify")
    def test_rearms_below_threshold(self, mock_notify, mgr):
        mgr.check(_make_usage_data(utilization=0.75))
        mgr.check(_make_usage_data(utilization=0.50))  # drop below
        mgr.check(_make_usage_data(utilization=0.80))  # cross again
        assert mock_notify.call_count == 2

    @patch("src.notifications.notification.notify")
    def test_disabled_no_notification(self, mock_notify, mgr):
        mgr.set_threshold_enabled(False)
        mgr.check(_make_usage_data(utilization=0.90))
        mock_notify.assert_not_called()

    @patch("src.notifications.notification.notify")
    def test_custom_threshold(self, mock_notify, mgr):
        mgr.update_threshold(0.90)
        mgr.check(_make_usage_data(utilization=0.85))
        mock_notify.assert_not_called()
        mgr.check(_make_usage_data(utilization=0.95))
        mock_notify.assert_called_once()

    @patch("src.notifications.notification.notify")
    def test_below_threshold_no_fire(self, mock_notify, mgr):
        mgr.check(_make_usage_data(utilization=0.50))
        mock_notify.assert_not_called()


# ── Reset alerts ─────────────────────────────────────────────────────────────


class TestResetAlerts:
    @patch("src.notifications.notification.notify")
    def test_fires_on_reset(self, mock_notify, mgr):
        mgr.set_reset_notifications(True)
        t1 = datetime.now(timezone.utc)
        t2 = t1 + timedelta(hours=5)

        mgr.check(_make_usage_data(utilization=0.3, resets_at=t1))
        mock_notify.assert_not_called()  # first check sets baseline

        mgr.check(_make_usage_data(utilization=0.1, resets_at=t2))
        mock_notify.assert_called_once()
        assert "reset" in mock_notify.call_args[1]["message"].lower()

    @patch("src.notifications.notification.notify")
    def test_no_fire_same_resets_at(self, mock_notify, mgr):
        mgr.set_reset_notifications(True)
        t1 = datetime.now(timezone.utc)
        mgr.check(_make_usage_data(utilization=0.3, resets_at=t1))
        mgr.check(_make_usage_data(utilization=0.3, resets_at=t1))
        mock_notify.assert_not_called()

    @patch("src.notifications.notification.notify")
    def test_disabled_no_fire(self, mock_notify, mgr):
        mgr.set_reset_notifications(False)
        t1 = datetime.now(timezone.utc)
        t2 = t1 + timedelta(hours=5)
        mgr.check(_make_usage_data(utilization=0.3, resets_at=t1))
        mgr.check(_make_usage_data(utilization=0.1, resets_at=t2))
        mock_notify.assert_not_called()

    @patch("src.notifications.notification.notify")
    def test_no_fire_when_above_threshold(self, mock_notify, mgr):
        mgr.set_reset_notifications(True)
        t1 = datetime.now(timezone.utc)
        t2 = t1 + timedelta(hours=5)
        mgr.check(_make_usage_data(utilization=0.3, resets_at=t1))
        # Above threshold at reset → no reset notification
        mgr.check(_make_usage_data(utilization=0.80, resets_at=t2))
        # Only the threshold notification fires, not the reset one
        calls = [c[1]["message"] for c in mock_notify.call_args_list]
        assert not any("reset" in m.lower() for m in calls)


# ── 7-day threshold alerts ───────────────────────────────────────────────────


class TestSevenDayThresholdAlerts:
    @patch("src.notifications.notification.notify")
    def test_fires_when_crossing(self, mock_notify, mgr):
        mgr.set_threshold_enabled(False)  # disable 5h to isolate
        data = _make_usage_data(seven_day_util=0.75)
        mgr.check(data)
        mock_notify.assert_called_once()
        assert "7d" in mock_notify.call_args[1]["message"]
        assert "75%" in mock_notify.call_args[1]["message"]

    @patch("src.notifications.notification.notify")
    def test_no_duplicate(self, mock_notify, mgr):
        mgr.set_threshold_enabled(False)
        data = _make_usage_data(seven_day_util=0.75)
        mgr.check(data)
        mgr.check(data)
        assert mock_notify.call_count == 1

    @patch("src.notifications.notification.notify")
    def test_rearms_below_threshold(self, mock_notify, mgr):
        mgr.set_threshold_enabled(False)
        mgr.check(_make_usage_data(seven_day_util=0.75))
        mgr.check(_make_usage_data(seven_day_util=0.50))
        mgr.check(_make_usage_data(seven_day_util=0.80))
        assert mock_notify.call_count == 2

    @patch("src.notifications.notification.notify")
    def test_disabled_no_notification(self, mock_notify, mgr):
        mgr.set_threshold_enabled(False)
        mgr.set_seven_day_threshold_enabled(False)
        mgr.check(_make_usage_data(seven_day_util=0.90))
        mock_notify.assert_not_called()

    @patch("src.notifications.notification.notify")
    def test_custom_threshold(self, mock_notify, mgr):
        mgr.set_threshold_enabled(False)
        mgr.update_seven_day_threshold(0.90)
        mgr.check(_make_usage_data(seven_day_util=0.85))
        mock_notify.assert_not_called()
        mgr.check(_make_usage_data(seven_day_util=0.95))
        mock_notify.assert_called_once()

    @patch("src.notifications.notification.notify")
    def test_below_threshold_no_fire(self, mock_notify, mgr):
        mgr.set_threshold_enabled(False)
        mgr.check(_make_usage_data(seven_day_util=0.50))
        mock_notify.assert_not_called()


# ── 7-day reset alerts ──────────────────────────────────────────────────────


class TestSevenDayResetAlerts:
    @patch("src.notifications.notification.notify")
    def test_fires_on_reset(self, mock_notify, mgr):
        mgr.set_threshold_enabled(False)
        mgr.set_seven_day_reset_notifications(True)
        t1 = datetime.now(timezone.utc)
        t2 = t1 + timedelta(days=7)

        mgr.check(_make_usage_data(seven_day_util=0.3, seven_day_resets_at=t1))
        mock_notify.assert_not_called()

        mgr.check(_make_usage_data(seven_day_util=0.1, seven_day_resets_at=t2))
        mock_notify.assert_called_once()
        assert "7d" in mock_notify.call_args[1]["message"]
        assert "reset" in mock_notify.call_args[1]["message"].lower()

    @patch("src.notifications.notification.notify")
    def test_no_fire_same_resets_at(self, mock_notify, mgr):
        mgr.set_threshold_enabled(False)
        mgr.set_seven_day_reset_notifications(True)
        t1 = datetime.now(timezone.utc)
        mgr.check(_make_usage_data(seven_day_util=0.3, seven_day_resets_at=t1))
        mgr.check(_make_usage_data(seven_day_util=0.3, seven_day_resets_at=t1))
        mock_notify.assert_not_called()

    @patch("src.notifications.notification.notify")
    def test_disabled_no_fire(self, mock_notify, mgr):
        mgr.set_threshold_enabled(False)
        mgr.set_seven_day_reset_notifications(False)
        t1 = datetime.now(timezone.utc)
        t2 = t1 + timedelta(days=7)
        mgr.check(_make_usage_data(seven_day_util=0.3, seven_day_resets_at=t1))
        mgr.check(_make_usage_data(seven_day_util=0.1, seven_day_resets_at=t2))
        mock_notify.assert_not_called()

    @patch("src.notifications.notification.notify")
    def test_no_fire_when_above_threshold(self, mock_notify, mgr):
        mgr.set_threshold_enabled(False)
        mgr.set_seven_day_reset_notifications(True)
        t1 = datetime.now(timezone.utc)
        t2 = t1 + timedelta(days=7)
        mgr.check(_make_usage_data(seven_day_util=0.3, seven_day_resets_at=t1))
        mgr.check(_make_usage_data(seven_day_util=0.80, seven_day_resets_at=t2))
        calls = [c[1]["message"] for c in mock_notify.call_args_list]
        assert not any("7d" in m and "reset" in m.lower() for m in calls)


# ── Settings persistence ────────────────────────────────────────────────────


class TestSettingsPersistence:
    def test_save_and_load(self, tmp_path):
        settings_file = tmp_path / "settings.json"
        with patch("src.notifications.SETTINGS_FILE", settings_file):
            with patch("src.notifications.APP_DATA_DIR", tmp_path):
                mgr1 = NotificationManager()
                mgr1.update_threshold(0.85)
                mgr1.set_threshold_enabled(False)
                mgr1.set_reset_notifications(True)
                mgr1.update_seven_day_threshold(0.90)
                mgr1.set_seven_day_threshold_enabled(False)
                mgr1.set_seven_day_reset_notifications(True)

                mgr2 = NotificationManager()
                assert mgr2.threshold == pytest.approx(0.85)
                assert mgr2.threshold_enabled is False
                assert mgr2.reset_notifications is True
                assert mgr2.seven_day_threshold == pytest.approx(0.90)
                assert mgr2.seven_day_threshold_enabled is False
                assert mgr2.seven_day_reset_notifications is True
