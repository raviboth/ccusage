# Task: Test UsageDB

**File:** `tests/test_db.py`
**Priority:** High
**Dependencies:** None

## What to test

Use a temp directory for the database file.

- **Insert and retrieve**: insert_snapshot with UsageData → data persists
- **Multiple inserts**: insert several snapshots → all stored
- **Prune old**: insert data older than DB_PRUNE_DAYS → prune_old() removes it
- **Prune keeps recent**: insert recent data → prune_old() keeps it
- **Close and reopen**: data survives across close/reopen
- **Schema creation**: fresh DB creates table without error
