# Feature Request: FR-FSM-017 Remove runtime sys.path.insert hacks

**Priority:** MEDIUM
**Type:** Cleanup / Bug
**Status:** Implemented (pending commit)
**Effort:** 0.5 days
**Requested:** 2026-05-12

## Summary

Six source files mutate `sys.path` at import time using
`sys.path.insert(0, str(Path(__file__).parent.parent))` to make
`from statemachine_engine.*` imports work. This is fragile, order-dependent,
and was already the root direction of the NC-290 incident (`No module named
'actions.real'`). The proper fix is to use fully-qualified package imports —
which work correctly now that the package is installed via `pip install -e .`.

## Problem

The following files contained runtime path manipulation:

| File | Hack |
|------|------|
| `core/engine.py` | `sys.path.insert(0, …parent.parent)` + `from database.models import …` |
| `actions/builtin/check_database_queue_action.py` | `sys.path.insert(0, …parent.parent)` |
| `actions/builtin/claim_job_action.py` | `sys.path.insert(0, …parent.parent)` |
| `actions/builtin/get_pending_jobs_action.py` | `sys.path.insert(0, …parent.parent)` |
| `database/cli.py` | `sys.path.insert(0, …parent.parent)` |
| `monitoring/websocket_server.py` | `sys.path.insert(0, …parent.parent.parent)` |

Side effects:
- The `sys.path` mutation is permanent for the process lifetime, affecting all
  subsequent imports unpredictably.
- Relative path arithmetic (`parent.parent`) breaks if the working directory or
  installation layout changes (e.g., editable vs. wheel install, Docker layer
  changes — as seen in NC-290).
- Static analysis tools (`ruff`, `mypy`) cannot resolve bare `database.models`
  imports; `from statemachine_engine.database.models import …` works correctly.

## Implemented Fix

Replace every instance with the proper fully-qualified package import:

```python
# Before (engine.py)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from database.models import get_realtime_event_model

# After
from statemachine_engine.database.models import get_realtime_event_model
```

The same pattern applies to all six files. Dead `import sys` and
`from pathlib import Path` lines are removed where they were only present to
support the path hack.

## Acceptance Criteria

- [ ] All `sys.path.insert` calls that exist solely for intra-package imports
      are removed from the six listed files
- [ ] All affected imports use `statemachine_engine.*` fully-qualified paths
- [ ] `pytest tests/ -v` passes (411+, 9 skipped)
- [ ] `ruff check src/` passes with no import-related warnings in those files
- [ ] Changes committed and released

## Status

Changes are present in the working tree (unstaged). Need to commit, bump
version, and release.

## Related

- NC-290: `No module named 'actions.real'` — same class of fragile path
  arithmetic in custom action imports
- FR-FSM-012: `action_loader.py` correctly uses package-relative import
  (`from .action_loader import get_action_loader`) — this FR extends the same
  discipline to the remaining six files
