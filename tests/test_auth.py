"""Tests for src/auth.py — token retrieval, expiry checking, and refresh."""

import json
import time
from unittest.mock import patch

import pytest

from src.auth import AuthResult, get_oauth_token


def _make_credentials(
    token="sk-test-token",
    refresh="sk-test-refresh",
    expires_at_ms=None,
    scopes=None,
):
    """Build a credential JSON string matching the keychain format."""
    oauth = {"accessToken": token}
    if refresh:
        oauth["refreshToken"] = refresh
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


# ── Token expiry and refresh ─────────────────────────────────────────────────


class TestTokenRefresh:
    @patch("src.auth._save_credentials")
    @patch("src.auth._refresh_token")
    @patch("src.auth._read_raw_credentials")
    def test_non_expired_skips_refresh(self, mock_read, mock_refresh, mock_save):
        mock_read.return_value = _make_credentials(
            token="sk-valid", expires_at_ms=_future_ms(3600)
        )
        result = get_oauth_token()
        assert result.access_token == "sk-valid"
        mock_refresh.assert_not_called()
        mock_save.assert_not_called()

    @patch("src.auth._save_credentials")
    @patch("src.auth._refresh_token")
    @patch("src.auth._read_raw_credentials")
    def test_expired_triggers_refresh(self, mock_read, mock_refresh, mock_save):
        mock_read.return_value = _make_credentials(
            token="sk-expired",
            refresh="sk-refresh",
            expires_at_ms=_past_ms(60),
            scopes=["user:inference"],
        )
        mock_refresh.return_value = {
            "access_token": "sk-new-token",
            "refresh_token": "sk-new-refresh",
            "expires_in": 28800,
        }
        result = get_oauth_token()
        assert result.access_token == "sk-new-token"
        assert result.error is None
        mock_refresh.assert_called_once_with("sk-refresh", ["user:inference"])
        mock_save.assert_called_once()
        # Verify saved JSON has updated tokens
        saved_json = json.loads(mock_save.call_args[0][0])
        assert saved_json["claudeAiOauth"]["accessToken"] == "sk-new-token"
        assert saved_json["claudeAiOauth"]["refreshToken"] == "sk-new-refresh"

    @patch("src.auth._save_credentials")
    @patch("src.auth._refresh_token")
    @patch("src.auth._read_raw_credentials")
    def test_expired_refresh_fails(self, mock_read, mock_refresh, mock_save):
        mock_read.return_value = _make_credentials(
            token="sk-expired",
            refresh="sk-refresh",
            expires_at_ms=_past_ms(60),
        )
        mock_refresh.return_value = None
        result = get_oauth_token()
        assert result.access_token is None
        assert "expired" in result.error.lower()
        mock_save.assert_not_called()

    @patch("src.auth._save_credentials")
    @patch("src.auth._refresh_token")
    @patch("src.auth._read_raw_credentials")
    def test_no_expires_at_skips_refresh(self, mock_read, mock_refresh, mock_save):
        mock_read.return_value = _make_credentials(token="sk-no-expiry")
        result = get_oauth_token()
        assert result.access_token == "sk-no-expiry"
        mock_refresh.assert_not_called()

    @patch("src.auth._save_credentials")
    @patch("src.auth._refresh_token")
    @patch("src.auth._read_raw_credentials")
    def test_expired_no_refresh_token(self, mock_read, mock_refresh, mock_save):
        mock_read.return_value = _make_credentials(
            token="sk-expired",
            refresh=None,
            expires_at_ms=_past_ms(60),
        )
        result = get_oauth_token()
        # No refresh token → falls through to return stale token
        assert result.access_token == "sk-expired"
        mock_refresh.assert_not_called()


# ── _refresh_token() ─────────────────────────────────────────────────────────


class TestRefreshToken:
    @patch("src.auth.requests.post")
    def test_success(self, mock_post):
        from src.auth import _refresh_token

        resp = type("Resp", (), {
            "status_code": 200,
            "json": lambda self: {
                "access_token": "sk-new",
                "refresh_token": "sk-new-refresh",
                "expires_in": 28800,
            },
        })()
        mock_post.return_value = resp
        result = _refresh_token("sk-old-refresh", ["user:inference"])
        assert result["access_token"] == "sk-new"

    @patch("src.auth.requests.post")
    def test_failure_status(self, mock_post):
        from src.auth import _refresh_token

        resp = type("Resp", (), {"status_code": 400})()
        mock_post.return_value = resp
        result = _refresh_token("sk-old-refresh", [])
        assert result is None

    @patch("src.auth.requests.post")
    def test_network_error(self, mock_post):
        import requests as req
        from src.auth import _refresh_token

        mock_post.side_effect = req.ConnectionError()
        result = _refresh_token("sk-old-refresh", [])
        assert result is None
