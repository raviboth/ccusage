"""Tests for src/api.py — _parse_window() and fetch_usage()."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.api import (
    ExtraUsage,
    UsageData,
    UsageResult,
    UsageWindow,
    _parse_window,
    fetch_usage,
)


# ── _parse_window() ──────────────────────────────────────────────────────────


class TestParseWindow:
    def test_normal(self):
        w = _parse_window({"utilization": 42, "resets_at": "2026-03-19T12:00:00+00:00"})
        assert w.utilization == pytest.approx(0.42)
        assert w.resets_at == datetime(2026, 3, 19, 12, 0, tzinfo=timezone.utc)

    def test_normalizes_percentage(self):
        w = _parse_window({"utilization": 100})
        assert w.utilization == pytest.approx(1.0)

    def test_over_100(self):
        w = _parse_window({"utilization": 150})
        assert w.utilization == pytest.approx(1.5)

    def test_zero(self):
        w = _parse_window({"utilization": 0})
        assert w.utilization == pytest.approx(0.0)
        assert w.resets_at is None

    def test_empty_dict(self):
        w = _parse_window({})
        assert w.utilization == pytest.approx(0.0)
        assert w.resets_at is None

    def test_none_input(self):
        w = _parse_window(None)
        assert w.utilization == pytest.approx(0.0)
        assert w.resets_at is None

    def test_bad_date(self):
        w = _parse_window({"utilization": 50, "resets_at": "not-a-date"})
        assert w.utilization == pytest.approx(0.5)
        assert w.resets_at is None

    def test_missing_resets_at(self):
        w = _parse_window({"utilization": 75})
        assert w.utilization == pytest.approx(0.75)
        assert w.resets_at is None


# ── fetch_usage() ────────────────────────────────────────────────────────────


def _make_response(status_code=200, json_data=None, headers=None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        http_error = requests.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_error
    else:
        resp.raise_for_status.return_value = None
    return resp


_FULL_BODY = {
    "five_hour": {"utilization": 42, "resets_at": "2026-03-19T12:00:00+00:00"},
    "seven_day": {"utilization": 10, "resets_at": "2026-03-25T00:00:00+00:00"},
}


class TestFetchUsageSuccess:
    @patch("src.api.requests.get")
    def test_success(self, mock_get):
        mock_get.return_value = _make_response(200, _FULL_BODY)
        result = fetch_usage("test-token")
        assert result.data is not None
        assert result.error is None
        assert result.data.five_hour.utilization == pytest.approx(0.42)
        assert result.data.seven_day.utilization == pytest.approx(0.10)
        assert result.data.seven_day_opus is None
        assert result.data.extra_usage is None

    @patch("src.api.requests.get")
    def test_with_opus(self, mock_get):
        body = {**_FULL_BODY, "seven_day_opus": {"utilization": 5}}
        mock_get.return_value = _make_response(200, body)
        result = fetch_usage("test-token")
        assert result.data.seven_day_opus is not None
        assert result.data.seven_day_opus.utilization == pytest.approx(0.05)

    @patch("src.api.requests.get")
    def test_with_extra_usage(self, mock_get):
        body = {
            **_FULL_BODY,
            "extra_usage": {
                "is_enabled": True,
                "monthly_limit": 5000,  # cents
                "used_credits": 1234,
                "utilization": 25,
            },
        }
        mock_get.return_value = _make_response(200, body)
        result = fetch_usage("test-token")
        assert result.data.extra_usage is not None
        assert result.data.extra_usage.monthly_limit == pytest.approx(50.0)
        assert result.data.extra_usage.used_credits == pytest.approx(12.34)
        assert result.data.extra_usage.utilization == pytest.approx(0.25)

    @patch("src.api.requests.get")
    def test_extra_usage_disabled(self, mock_get):
        body = {**_FULL_BODY, "extra_usage": {"is_enabled": False}}
        mock_get.return_value = _make_response(200, body)
        result = fetch_usage("test-token")
        assert result.data.extra_usage is None


class TestFetchUsageErrors:
    @patch("src.api.requests.get")
    def test_429_with_retry_after(self, mock_get):
        mock_get.return_value = _make_response(429, headers={"Retry-After": "30"})
        result = fetch_usage("test-token")
        assert result.data is None
        assert "429" in result.error
        assert result.retry_after == 120  # floored to 2 min

    @patch("src.api.requests.get")
    def test_429_without_retry_after(self, mock_get):
        mock_get.return_value = _make_response(429)
        result = fetch_usage("test-token")
        assert result.data is None
        assert "429" in result.error
        assert result.retry_after == 120

    @patch("src.api.requests.get")
    def test_429_with_large_retry_after(self, mock_get):
        mock_get.return_value = _make_response(429, headers={"Retry-After": "300"})
        result = fetch_usage("test-token")
        assert result.retry_after == 300

    @patch("src.api.requests.get")
    def test_429_with_non_digit_retry_after(self, mock_get):
        mock_get.return_value = _make_response(429, headers={"Retry-After": "abc"})
        result = fetch_usage("test-token")
        assert result.retry_after == 120

    @patch("src.api.requests.get")
    def test_http_500(self, mock_get):
        mock_get.return_value = _make_response(500)
        result = fetch_usage("test-token")
        assert result.data is None
        assert "500" in result.error
        assert result.retry_after is None

    @patch("src.api.requests.get")
    def test_timeout(self, mock_get):
        mock_get.side_effect = requests.Timeout()
        result = fetch_usage("test-token")
        assert result.data is None
        assert "timed out" in result.error

    @patch("src.api.requests.get")
    def test_connection_error(self, mock_get):
        mock_get.side_effect = requests.ConnectionError()
        result = fetch_usage("test-token")
        assert result.data is None
        assert "Could not connect" in result.error

    @patch("src.api.requests.get")
    def test_invalid_json(self, mock_get):
        resp = _make_response(200)
        resp.json.side_effect = ValueError("bad json")
        mock_get.return_value = resp
        result = fetch_usage("test-token")
        assert result.data is None
        assert "Invalid JSON" in result.error

    @patch("src.api.requests.get")
    def test_generic_request_exception(self, mock_get):
        mock_get.side_effect = requests.RequestException()
        result = fetch_usage("test-token")
        assert result.data is None
        assert "request failed" in result.error
