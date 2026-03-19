# Task: Test poll loop backoff logic

**File:** `tests/test_main.py`
**Priority:** Medium
**Dependencies:** None

## What to test

Test the wait-time calculation logic from `_poll_loop`. This may require extracting
the backoff logic into a testable function or testing via the App class with mocked
dependencies.

- **Success**: result.data present → wait is POLL_INTERVAL_SECONDS (300), consecutive_errors resets to 0
- **First error**: no data → wait is 300 * 2^1 = 600 (capped at 600)
- **Second error**: → wait is 600 (capped)
- **429 with retry_after=120**: → wait is max(120, 300) = 300
- **429 with retry_after=600**: → wait is max(600, 300) = 600
- **Error then success**: consecutive_errors resets to 0, wait returns to normal
- **Auth error (returns None)**: → treated as error, backs off
