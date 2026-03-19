import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from src.constants import (
    KEYCHAIN_SERVICE_NAME,
    OAUTH_CLIENT_ID,
    OAUTH_TOKEN_URL,
)


@dataclass
class AuthResult:
    access_token: str | None
    error: str | None


def get_oauth_token() -> AuthResult:
    """Retrieve the Claude Code OAuth token from the system credential store.

    If the token is expired or expiring soon, attempt to refresh it
    using the stored refresh token and save the new credentials back.
    """
    raw = _read_raw_credentials()
    if raw is None:
        return AuthResult(
            access_token=None,
            error="No Claude Code credentials found. Run Claude Code to log in.",
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

    # Only refresh if the token is fully expired -- avoid racing with
    # Claude Code sessions that also refresh (refresh tokens are single-use,
    # so concurrent refreshes can invalidate each other).
    expires_at_ms = oauth_data.get("expiresAt")
    if expires_at_ms:
        now_ms = time.time() * 1000
        if now_ms >= expires_at_ms:
            refresh_token = oauth_data.get("refreshToken")
            scopes = oauth_data.get("scopes", [])
            if refresh_token:
                refreshed = _refresh_token(refresh_token, scopes)
                if refreshed:
                    # Update credentials in-place and save back
                    oauth_data["accessToken"] = refreshed["access_token"]
                    oauth_data["refreshToken"] = refreshed["refresh_token"]
                    oauth_data["expiresAt"] = int(
                        (time.time() + refreshed["expires_in"]) * 1000
                    )
                    _save_credentials(json.dumps(data))
                    return AuthResult(
                        access_token=refreshed["access_token"], error=None
                    )
                return AuthResult(
                    access_token=None,
                    error="Token expired and refresh failed.\nRestart Claude Code to re-authenticate.",
                )

    return AuthResult(access_token=token, error=None)


def _refresh_token(refresh_token: str, scopes: list[str]) -> dict | None:
    """Attempt to refresh the OAuth token. Returns new token dict or None."""
    try:
        resp = requests.post(
            OAUTH_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": OAUTH_CLIENT_ID,
                "scope": " ".join(scopes) if scopes else "",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except requests.RequestException:
        pass
    return None


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


def _save_credentials(raw_json: str) -> None:
    """Save updated credentials back to the system credential store."""
    if sys.platform == "darwin":
        _save_keychain_macos(raw_json)
    else:
        _save_credentials_linux(raw_json)


def _save_keychain_macos(raw_json: str) -> None:
    try:
        # Delete then re-add (macOS security doesn't have a simple update)
        subprocess.run(
            ["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE_NAME],
            capture_output=True,
            timeout=5,
        )
        subprocess.run(
            [
                "security",
                "add-generic-password",
                "-s",
                KEYCHAIN_SERVICE_NAME,
                "-a",
                _get_keychain_account(),
                "-w",
                raw_json,
            ],
            capture_output=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass


def _save_credentials_linux(raw_json: str) -> None:
    credentials_file = Path.home() / ".claude" / ".credentials.json"
    try:
        credentials_file.write_text(raw_json)
    except OSError:
        pass


def _get_keychain_account() -> str:
    """Get the account name from the existing keychain entry."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE_NAME],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if '"acct"' in line:
                    # Extract value: "acct"<blob>="username"
                    start = line.rfind('"', 0, len(line) - 1)
                    if start > line.index("="):
                        return line[start + 1 : -1]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return ""
