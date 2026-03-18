from dataclasses import dataclass
from datetime import datetime, timezone

import requests

from src.constants import API_TIMEOUT_SECONDS, USAGE_API_BETA_HEADER, USAGE_API_URL


@dataclass
class UsageWindow:
    utilization: float  # 0.0 to 1.0+ (normalized from API's 0-100 scale)
    resets_at: datetime | None


@dataclass
class ExtraUsage:
    is_enabled: bool
    monthly_limit: float
    used_credits: float
    utilization: float  # 0.0 to 1.0+


@dataclass
class UsageData:
    five_hour: UsageWindow
    seven_day: UsageWindow
    seven_day_opus: UsageWindow | None
    extra_usage: ExtraUsage | None
    fetched_at: datetime


@dataclass
class UsageResult:
    data: UsageData | None
    error: str | None
    retry_after: int | None = None


def fetch_usage(access_token: str) -> UsageResult:
    """Fetch current usage from the Anthropic OAuth usage endpoint.

    The access_token is used only for this request and not stored.
    Authorization headers are stripped from any error messages.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "anthropic-beta": USAGE_API_BETA_HEADER,
        "Accept": "application/json",
    }

    try:
        resp = requests.get(
            USAGE_API_URL, headers=headers, timeout=API_TIMEOUT_SECONDS
        )
        resp.raise_for_status()
    except requests.Timeout:
        return UsageResult(data=None, error="API request timed out.")
    except requests.ConnectionError:
        return UsageResult(data=None, error="Could not connect to Anthropic API.")
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        if status == 429:
            retry_after = None
            if e.response is not None:
                raw = e.response.headers.get("Retry-After")
                if raw and raw.isdigit():
                    retry_after = max(int(raw), 120)  # floor at 2 min
                else:
                    retry_after = 120
            return UsageResult(
                data=None,
                error="Rate limited (429).\nToo many sessions may be sharing the quota.",
                retry_after=retry_after,
            )
        return UsageResult(data=None, error=f"API returned HTTP {status}.")
    except requests.RequestException:
        return UsageResult(data=None, error="API request failed.")

    try:
        body = resp.json()
    except ValueError:
        return UsageResult(data=None, error="Invalid JSON response from API.")

    extra = body.get("extra_usage")
    extra_usage = None
    if extra and extra.get("is_enabled"):
        extra_usage = ExtraUsage(
            is_enabled=True,
            monthly_limit=extra.get("monthly_limit", 0) / 100.0,  # cents to dollars
            used_credits=extra.get("used_credits", 0) / 100.0,  # cents to dollars
            utilization=extra.get("utilization", 0) / 100.0,
        )

    return UsageResult(
        data=UsageData(
            five_hour=_parse_window(body.get("five_hour", {})),
            seven_day=_parse_window(body.get("seven_day", {})),
            seven_day_opus=_parse_window(body.get("seven_day_opus"))
            if body.get("seven_day_opus")
            else None,
            extra_usage=extra_usage,
            fetched_at=datetime.now(timezone.utc),
        ),
        error=None,
    )


def _parse_window(data: dict | None) -> UsageWindow:
    if not data:
        return UsageWindow(utilization=0.0, resets_at=None)

    # API returns utilization as percentage (0-100+), normalize to 0.0-1.0+
    util = data.get("utilization", 0.0) / 100.0
    resets_at_str = data.get("resets_at")
    resets_at = None
    if resets_at_str:
        try:
            resets_at = datetime.fromisoformat(resets_at_str)
        except ValueError:
            pass

    return UsageWindow(utilization=util, resets_at=resets_at)
