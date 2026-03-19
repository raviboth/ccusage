# Task: Test auth keychain/credential store integration

**File:** `tests/test_auth.py`
**Priority:** Medium
**Dependencies:** None

## What to test

Mock `subprocess.run` for keychain calls.

### macOS (mock `security` command)
- Successful read → returns credential JSON
- `security` returns non-zero → returns None
- `security` times out → returns None
- `security` not found → returns None

### Linux (mock file + `secret-tool`)
- ~/.claude/.credentials.json exists → reads from file
- File doesn't exist, secret-tool succeeds → reads from secret-tool
- Neither available → returns None

### Credential parsing
- Nested format: `{"claudeAiOauth": {"accessToken": "..."}}`
- Flat format: `{"access_token": "..."}`
- Missing token → error
- Invalid JSON → error

### Save credentials
- macOS: mock security delete + add → verify called with correct args
- Linux: verify file written
- _get_keychain_account() extracts account name from security output
