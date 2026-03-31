"""Tests for src/auth.py — token retrieval."""

import json
from unittest.mock import patch

import pytest

from src.auth import AuthResult, get_oauth_token


def _make_credentials(token="sk-test-token"):
    """Build a credential JSON string matching the keychain format."""
    return json.dumps({"claudeAiOauth": {"accessToken": token}})


# ── Basic credential reading ────────────────────────────────────────────────


class TestGetOAuthToken:
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

    @patch("src.auth._read_raw_credentials")
    def test_returns_token_regardless_of_expiry(self, mock_read):
        """Token is returned even if expiresAt is in the past — API handles rejection."""
        import time
        past_ms = int((time.time() - 3600) * 1000)
        creds = json.dumps({"claudeAiOauth": {"accessToken": "sk-stale", "expiresAt": past_ms}})
        mock_read.return_value = creds
        result = get_oauth_token()
        assert result.access_token == "sk-stale"
        assert result.error is None
