# Task: Test NotificationManager

**File:** `tests/test_notifications.py`
**Priority:** High
**Dependencies:** None

## What to test

Mock `plyer.notification.notify` to capture calls.

### Threshold alerts
- Utilization crosses threshold (e.g., 70%) → notification fires once
- Utilization stays above threshold on subsequent checks → no duplicate notification
- Utilization drops below threshold then rises above → notification fires again (re-armed)
- Threshold alerts disabled → no notification even when crossing
- Custom threshold value (e.g., 90%) → fires at 90%, not 70%

### Reset alerts
- resets_at changes to a new value → "window has reset" notification
- resets_at unchanged → no notification
- Reset alerts disabled → no notification
- Reset while above threshold → no reset notification (by design)

### Settings
- update_threshold() changes the threshold
- set_threshold_enabled() toggles alerts
- set_reset_notifications() toggles reset alerts
