import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from src.constants import KEYCHAIN_SERVICE_NAME


@dataclass
class AuthResult:
    access_token: str | None
    error: str | None


def get_oauth_token() -> AuthResult:
    """Retrieve the Claude Code OAuth token from the system credential store.

    If the token is expired, returns an error directing the user to open
    Claude Code to refresh it. We never refresh the token ourselves to
    avoid invalidating the refresh token and logging out active sessions.
    """
    raw = _read_raw_credentials()
    if raw is None:
        return AuthResult(
            access_token=None,
            error="No Claude Code credentials found.\nRun Claude Code to log in.",
        )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return AuthResult(
            access_token=None,
            error="Failed to parse credentials JSON.",
        )

    oauth_data = data.get("claudeAiOauth", data)
    token = (
        oauth_data.get("accessToken")
        or oauth_data.get("access_token")
        or data.get("access_token")
    )
    if not token:
        return AuthResult(
            access_token=None,
            error="Credentials found but no access_token present.",
        )

    # Check if token is expired
    expires_at_ms = oauth_data.get("expiresAt")
    if expires_at_ms:
        now_ms = time.time() * 1000
        if now_ms >= expires_at_ms:
            return AuthResult(
                access_token=None,
                error="Token expired.\nOpen Claude Code to refresh.",
            )

    return AuthResult(access_token=token, error=None)


def _read_raw_credentials() -> str | None:
    """Read raw credential JSON from the system credential store."""
    if sys.platform == "darwin":
        return _read_keychain_macos()
    else:
        return _read_credentials_linux()


def _read_keychain_macos() -> str | None:
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE_NAME, "-w"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _read_credentials_linux() -> str | None:
    credentials_file = Path.home() / ".claude" / ".credentials.json"
    if credentials_file.exists():
        try:
            return credentials_file.read_text()
        except OSError:
            pass

    try:
        result = subprocess.run(
            ["secret-tool", "lookup", "service", KEYCHAIN_SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
