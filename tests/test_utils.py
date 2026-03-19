"""Tests for src/utils.py — color selection and time formatting."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from src.constants import COLOR_GREEN, COLOR_GREY, COLOR_RED, COLOR_YELLOW
from src.utils import (
    color_for_utilization,
    format_reset_time,
    format_reset_time_verbose,
    format_utilization,
    format_utilization_label,
)


# ── color_for_utilization() ──────────────────────────────────────────────────


class TestColorForUtilization:
    def test_none(self):
        assert color_for_utilization(None) == COLOR_GREY

    def test_zero(self):
        assert color_for_utilization(0.0) == COLOR_GREEN

    def test_below_yellow(self):
        assert color_for_utilization(0.59) == COLOR_GREEN

    def test_at_yellow_boundary(self):
        assert color_for_utilization(0.60) == COLOR_YELLOW

    def test_mid_yellow(self):
        assert color_for_utilization(0.79) == COLOR_YELLOW

    def test_at_red_boundary(self):
        assert color_for_utilization(0.80) == COLOR_RED

    def test_full(self):
        assert color_for_utilization(1.0) == COLOR_RED

    def test_over_100(self):
        assert color_for_utilization(1.5) == COLOR_RED


# ── format_utilization() ─────────────────────────────────────────────────────


class TestFormatUtilization:
    def test_zero(self):
        assert format_utilization(0.0) == "0%"

    def test_normal(self):
        assert format_utilization(0.42) == "42%"

    def test_full(self):
        assert format_utilization(1.0) == "100%"

    def test_over_100(self):
        assert format_utilization(1.5) == "100+%"


# ── format_utilization_label() ───────────────────────────────────────────────


class TestFormatUtilizationLabel:
    def test_none(self):
        assert format_utilization_label(None) == "?"

    def test_normal(self):
        assert format_utilization_label(0.42) == "42"

    def test_over_100(self):
        assert format_utilization_label(1.5) == "100+"


# ── format_reset_time() ─────────────────────────────────────────────────────


class TestFormatResetTime:
    def test_none(self):
        assert format_reset_time(None) == "no reset scheduled"

    def test_past(self):
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        assert format_reset_time(past) == "resetting now"

    def test_hours_and_minutes(self):
        future = datetime.now(timezone.utc) + timedelta(hours=2, minutes=15, seconds=30)
        result = format_reset_time(future)
        assert "2h" in result
        assert "m" in result  # has minutes component

    def test_days(self):
        future = datetime.now(timezone.utc) + timedelta(days=3, hours=5, seconds=30)
        result = format_reset_time(future)
        assert "3d" in result
        assert "h" in result  # has hours component
        # Minutes hidden when days > 0
        assert "m" not in result

    def test_just_seconds(self):
        future = datetime.now(timezone.utc) + timedelta(seconds=30)
        result = format_reset_time(future)
        assert result == "resets soon"


# ── format_reset_time_verbose() ──────────────────────────────────────────────


class TestFormatResetTimeVerbose:
    def test_none(self):
        assert format_reset_time_verbose(None) == "No reset scheduled"

    def test_past(self):
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        assert format_reset_time_verbose(past) == "Resetting now"

    def test_future_today(self):
        future = datetime.now(timezone.utc) + timedelta(hours=2, minutes=15)
        result = format_reset_time_verbose(future)
        assert "Resets in" in result
        assert "2h" in result
        assert "\u00b7" in result  # middle dot separator

    def test_future_days(self):
        future = datetime.now(timezone.utc) + timedelta(days=3, hours=5, seconds=30)
        result = format_reset_time_verbose(future)
        assert "3d" in result
        assert "h" in result
