# Task: Test color_for_utilization()

**File:** `tests/test_utils.py`
**Priority:** High
**Dependencies:** None

## What to test

- 0.0 → green
- 0.59 → green
- 0.60 → yellow (exact boundary)
- 0.79 → yellow
- 0.80 → red (exact boundary)
- 1.0 → red
- 1.5 → red (over 100%)
