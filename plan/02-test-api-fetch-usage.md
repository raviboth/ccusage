# Task: Test fetch_usage() error handling

**File:** `tests/test_api.py`
**Priority:** High
**Dependencies:** None

## What to test

Use `unittest.mock.patch` to mock `requests.get`.

- **Success**: Mock 200 with full JSON body → returns UsageResult with populated UsageData
- **429 with Retry-After header**: Mock HTTPError with 429 + `Retry-After: 30` → error contains "Rate limited", retry_after is 120 (floored)
- **429 without Retry-After**: Mock HTTPError with 429, no header → retry_after is 120
- **429 with large Retry-After**: `Retry-After: 300` → retry_after is 300
- **Other HTTP error (500)**: → error says "API returned HTTP 500", retry_after is None
- **Timeout**: Mock `requests.Timeout` → error says "timed out"
- **Connection error**: Mock `requests.ConnectionError` → error says "Could not connect"
- **Invalid JSON**: Mock 200 but `resp.json()` raises ValueError → error says "Invalid JSON"
- **Extra usage parsing**: Body with `extra_usage.is_enabled: true` → ExtraUsage populated
- **Extra usage disabled**: Body with `extra_usage.is_enabled: false` → extra_usage is None
- **seven_day_opus present**: Body includes seven_day_opus → parsed
- **seven_day_opus absent**: Body without seven_day_opus → None
