# Task: Test dashboard UI

**File:** `tests/test_dashboard.py`
**Priority:** Low
**Dependencies:** PyQt6 test harness

## What to test

Requires `QApplication` instance in test setup.

- **update_usage()**: UsageData updates all bars, shows/hides opus and extra bars correctly
- **update_error()**: Sets error text with word wrap
- **update_status_time()**: Shows "X seconds ago" / "X minutes ago"
- **UsageBar.update_data()**: Progress bar value, color changes at thresholds, percentage label
- **Alert settings**: update_alert_settings() populates checkbox and spin values
- **closeEvent**: Window hides instead of closing

## Notes

These are lower priority since they require a Qt event loop and are harder to
run in CI. Consider whether the coverage is worth the test infrastructure cost.
