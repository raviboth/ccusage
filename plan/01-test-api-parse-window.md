# Task: Test _parse_window()

**File:** `tests/test_api.py`
**Priority:** High
**Dependencies:** None

## What to test

- Normal response: `{"utilization": 42, "resets_at": "2026-03-19T12:00:00+00:00"}` → `UsageWindow(0.42, datetime)`
- Utilization normalization: API sends 0-100 scale, we normalize to 0.0-1.0
- Over 100%: `{"utilization": 150}` → `UsageWindow(1.5, None)`
- Zero utilization: `{"utilization": 0}` → `UsageWindow(0.0, None)`
- Missing fields: `{}` → `UsageWindow(0.0, None)`
- None input: `_parse_window(None)` → `UsageWindow(0.0, None)`
- Bad date: `{"utilization": 50, "resets_at": "not-a-date"}` → resets_at is None
- Missing resets_at: `{"utilization": 50}` → resets_at is None
