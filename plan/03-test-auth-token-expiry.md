# Task: Test auth token expiry and refresh logic

**File:** `tests/test_auth.py`
**Priority:** High
**Dependencies:** None

## What to test

Mock `_read_raw_credentials` and `_refresh_token` and `_save_credentials`.

- **Valid non-expired token**: expiresAt in future → returns token, no refresh called
- **Expired token, refresh succeeds**: expiresAt in past, mock refresh returns new token → returns new token, _save_credentials called with updated JSON
- **Expired token, refresh fails**: expiresAt in past, mock refresh returns None → error about expired token
- **Expired token, no refresh token**: expiresAt in past, no refreshToken in data → error
- **No expiresAt field**: should return token without attempting refresh
- **No credentials found**: _read_raw_credentials returns None → error
- **Invalid JSON**: _read_raw_credentials returns garbage → error
- **Missing accessToken**: valid JSON but no token field → error
- **Credential formats**: test both `{"claudeAiOauth": {"accessToken": ...}}` and flat `{"access_token": ...}`
