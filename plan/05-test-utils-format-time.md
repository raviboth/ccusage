# Task: Test format_reset_time_verbose()

**File:** `tests/test_utils.py`
**Priority:** High
**Dependencies:** None

## What to test

- None input → empty string or appropriate fallback
- Reset time in the future (e.g., 2h 15m from now) → "Resets in 2h 15m" or similar
- Reset time just passed → handles gracefully (no negative times)
- Reset time exactly now → edge case
- Reset time far in the future (e.g., 6 days) → shows days
