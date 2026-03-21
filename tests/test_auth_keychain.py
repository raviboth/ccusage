"""Tests for src/auth.py — keychain/credential store integration (task 08)."""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from src.auth import (
    _read_credentials_linux,
    _read_keychain_macos,
)


# ── macOS keychain reading ───────────────────────────────────────────────────


class TestReadKeychainMacOS:
    @patch("src.auth.subprocess.run")
    def test_success(self, mock_run):
        creds = json.dumps({"claudeAiOauth": {"accessToken": "sk-test"}})
        mock_run.return_value = MagicMock(returncode=0, stdout=creds)
        result = _read_keychain_macos()
        assert result == creds

    @patch("src.auth.subprocess.run")
    def test_not_found(self, mock_run):
        mock_run.return_value = MagicMock(returncode=44, stdout="")
        result = _read_keychain_macos()
        assert result is None

    @patch("src.auth.subprocess.run")
    def test_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="security", timeout=5)
        result = _read_keychain_macos()
        assert result is None

    @patch("src.auth.subprocess.run")
    def test_command_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        result = _read_keychain_macos()
        assert result is None


# ── Linux credential reading ────────────────────────────────────────────────


class TestReadCredentialsLinux:
    def test_file_exists(self, tmp_path):
        creds = json.dumps({"claudeAiOauth": {"accessToken": "sk-linux"}})
        cred_file = tmp_path / ".claude" / ".credentials.json"
        cred_file.parent.mkdir(parents=True)
        cred_file.write_text(creds)
        with patch("src.auth.Path.home", return_value=tmp_path):
            result = _read_credentials_linux()
        assert result == creds

    @patch("src.auth.subprocess.run")
    def test_file_missing_falls_to_secret_tool(self, mock_run, tmp_path):
        creds = json.dumps({"claudeAiOauth": {"accessToken": "sk-secret"}})
        mock_run.return_value = MagicMock(returncode=0, stdout=creds)
        with patch("src.auth.Path.home", return_value=tmp_path):
            result = _read_credentials_linux()
        assert result == creds
        mock_run.assert_called_once()

    @patch("src.auth.subprocess.run")
    def test_both_missing(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        with patch("src.auth.Path.home", return_value=tmp_path):
            result = _read_credentials_linux()
        assert result is None

    @patch("src.auth.subprocess.run")
    def test_secret_tool_not_found(self, mock_run, tmp_path):
        mock_run.side_effect = FileNotFoundError()
        with patch("src.auth.Path.home", return_value=tmp_path):
            result = _read_credentials_linux()
        assert result is None

    @patch("src.auth.subprocess.run")
    def test_secret_tool_timeout(self, mock_run, tmp_path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="secret-tool", timeout=5)
        with patch("src.auth.Path.home", return_value=tmp_path):
            result = _read_credentials_linux()
        assert result is None
