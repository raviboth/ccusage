import json
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class AuthResult:
    access_token: str | None
    error: str | None


def get_oauth_token() -> AuthResult:
    """Retrieve the Claude Code OAuth token from the system credential store.

    Returns an AuthResult with the token or an error message.
    The token is never logged or persisted.
    """
    if sys.platform == "darwin":
        return _get_token_macos()
    else:
        return _get_token_linux()


def _get_token_macos() -> AuthResult:
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                "Claude Code-credentials",
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return AuthResult(
                access_token=None,
                error="No Claude Code credentials found in Keychain. Run Claude Code to log in.",
            )
        return _parse_credential_json(result.stdout.strip())
    except subprocess.TimeoutExpired:
        return AuthResult(access_token=None, error="Keychain access timed out.")
    except FileNotFoundError:
        return AuthResult(
            access_token=None, error="'security' command not found."
        )


def _get_token_linux() -> AuthResult:
    try:
        result = subprocess.run(
            [
                "secret-tool",
                "lookup",
                "service",
                "Claude Code-credentials",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return AuthResult(
                access_token=None,
                error="No Claude Code credentials found. Run Claude Code to log in.",
            )
        return _parse_credential_json(result.stdout.strip())
    except subprocess.TimeoutExpired:
        return AuthResult(access_token=None, error="Credential store access timed out.")
    except FileNotFoundError:
        return AuthResult(
            access_token=None,
            error="'secret-tool' not found. Install libsecret-tools.",
        )


def _parse_credential_json(raw: str) -> AuthResult:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return AuthResult(
            access_token=None,
            error="Failed to parse credentials JSON.",
        )

    # Credentials are nested: {"claudeAiOauth": {"accessToken": "..."}}
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

    return AuthResult(access_token=token, error=None)
