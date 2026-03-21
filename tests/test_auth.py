"""Tests for src/auth.py — token retrieval and expiry checking."""

import json
import time
from unittest.mock import patch

import pytest

from src.auth import AuthResult, get_oauth_token


def _make_credentials(
    token="sk-test-token",
    expires_at_ms=None,
    scopes=None,
):
    """Build a credential JSON string matching the keychain format."""
    oauth = {"accessToken": token}
    if expires_at_ms is not None:
        oauth["expiresAt"] = expires_at_ms
    if scopes:
        oauth["scopes"] = scopes
    return json.dumps({"claudeAiOauth": oauth})


def _future_ms(seconds=3600):
    return int((time.time() + seconds) * 1000)


def _past_ms(seconds=3600):
    return int((time.time() - seconds) * 1000)


# ── Basic credential reading ────────────────────────────────────────────────


class TestGetOAuthTokenBasic:
    @patch("src.auth._read_raw_credentials")
    def test_no_credentials(self, mock_read):
        mock_read.return_value = None
        result = get_oauth_token()
        assert result.access_token is None
        assert "No Claude Code credentials" in result.error

    @patch("src.auth._read_raw_credentials")
    def test_invalid_json(self, mock_read):
        mock_read.return_value = "not json{{"
        result = get_oauth_token()
        assert result.access_token is None
        assert "Failed to parse" in result.error

    @patch("src.auth._read_raw_credentials")
    def test_missing_token(self, mock_read):
        mock_read.return_value = json.dumps({"claudeAiOauth": {}})
        result = get_oauth_token()
        assert result.access_token is None
        assert "no access_token" in result.error

    @patch("src.auth._read_raw_credentials")
    def test_nested_format(self, mock_read):
        mock_read.return_value = _make_credentials(token="sk-nested")
        result = get_oauth_token()
        assert result.access_token == "sk-nested"
        assert result.error is None

    @patch("src.auth._read_raw_credentials")
    def test_flat_format(self, mock_read):
        mock_read.return_value = json.dumps({"access_token": "sk-flat"})
        result = get_oauth_token()
        assert result.access_token == "sk-flat"
        assert result.error is None


# ── Token expiry ─────────────────────────────────────────────────────────────


class TestTokenExpiry:
    @patch("src.auth._read_raw_credentials")
    def test_non_expired_returns_token(self, mock_read):
        mock_read.return_value = _make_credentials(
            token="sk-valid", expires_at_ms=_future_ms(3600)
        )
        result = get_oauth_token()
        assert result.access_token == "sk-valid"
        assert result.error is None

    @patch("src.auth._read_raw_credentials")
    def test_expired_returns_error(self, mock_read):
        mock_read.return_value = _make_credentials(
            token="sk-expired", expires_at_ms=_past_ms(60)
        )
        result = get_oauth_token()
        assert result.access_token is None
        assert "expired" in result.error.lower()
        assert "Claude Code" in result.error

    @patch("src.auth._read_raw_credentials")
    def test_no_expires_at_returns_token(self, mock_read):
        mock_read.return_value = _make_credentials(token="sk-no-expiry")
        result = get_oauth_token()
        assert result.access_token == "sk-no-expiry"
        assert result.error is None
