# Test Plan

Numbered tasks for adding test coverage to the app. Files are ordered by priority.

| # | Task | Priority | File |
|---|------|----------|------|
| 01 | _parse_window() | High | tests/test_api.py |
| 02 | fetch_usage() errors | High | tests/test_api.py |
| 03 | Auth token expiry/refresh | High | tests/test_auth.py |
| 04 | color_for_utilization() | High | tests/test_utils.py |
| 05 | format_reset_time_verbose() | High | tests/test_utils.py |
| 06 | NotificationManager | High | tests/test_notifications.py |
| 07 | UsageDB | High | tests/test_db.py |
| 08 | Auth keychain integration | Medium | tests/test_auth.py |
| 09 | Poll loop backoff | Medium | tests/test_main.py |
| 10 | Dashboard UI | Low | tests/test_dashboard.py |

## Running

```bash
source .venv/bin/activate
pip install pytest
pytest tests/
```
