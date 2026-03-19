"""Tests for poll loop backoff logic (task 09)."""

import pytest

from src.api import UsageData, UsageResult, UsageWindow
from src.main import compute_backoff
from datetime import datetime, timezone


def _success_result():
    return UsageResult(
        data=UsageData(
            five_hour=UsageWindow(utilization=0.5, resets_at=None),
            seven_day=UsageWindow(utilization=0.1, resets_at=None),
            seven_day_opus=None,
            extra_usage=None,
            fetched_at=datetime.now(timezone.utc),
        ),
        error=None,
    )


def _error_result(retry_after=None):
    return UsageResult(data=None, error="some error", retry_after=retry_after)


POLL = 300  # matches POLL_INTERVAL_SECONDS


class TestComputeBackoff:
    def test_success_resets_errors(self):
        errors, wait = compute_backoff(_success_result(), 3, POLL)
        assert errors == 0
        assert wait == POLL

    def test_first_error(self):
        errors, wait = compute_backoff(_error_result(), 0, POLL)
        assert errors == 1
        assert wait == min(POLL * 2, 600)

    def test_second_error(self):
        errors, wait = compute_backoff(_error_result(), 1, POLL)
        assert errors == 2
        assert wait == 600  # 300 * 4 = 1200, capped at 600

    def test_max_consecutive_errors(self):
        errors, wait = compute_backoff(_error_result(), 5, POLL)
        assert errors == 5  # capped at 5
        assert wait == 600

    def test_429_with_retry_after_below_poll(self):
        errors, wait = compute_backoff(_error_result(retry_after=120), 0, POLL)
        assert errors == 1
        assert wait == POLL  # max(120, 300) = 300

    def test_429_with_retry_after_above_poll(self):
        errors, wait = compute_backoff(_error_result(retry_after=600), 0, POLL)
        assert errors == 1
        assert wait == 600  # max(600, 300) = 600

    def test_none_result_treated_as_error(self):
        errors, wait = compute_backoff(None, 0, POLL)
        assert errors == 1

    def test_success_after_errors(self):
        errors, wait = compute_backoff(_success_result(), 5, POLL)
        assert errors == 0
        assert wait == POLL
