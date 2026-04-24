# Feature Request: Cache ActionLoader — stop per-execution instantiation

**Priority:** HIGH
**Type:** Bug / Performance
**Status:** Approved (scope reduced)
**Effort:** 0.5 days
**Requested:** 2026-04-24
**Judged:** 2026-04-24

## Summary

`engine.py` creates a new `ActionLoader` instance on every action execution
(`loader = ActionLoader(...)`).  `ActionLoader.__init__` runs a full filesystem
discovery and emits `logger.info("Action loader initialized: …")`.  With 12
active machines each firing actions every ~500 ms the log is flooded with ~24
"Action loader initialized" lines per second, `last_event` ages grow to 46 s+,
and useful signal (call/speech events, real errors) is buried.

## Value Statement

Operators can read logs without drowning in noise; real errors surface
immediately; and CPU time spent on repeated filesystem scans is eliminated.

## Problem

In `_execute_pluggable_action` (engine.py ≈ line 987–1000):

```python
loader = ActionLoader(actions_root=self.actions_root)   # ← new instance EVERY call
action_class = loader.load_action_class(action_type)
```

`ActionLoader.__init__` always:
1. Walks the built-in actions directory (`_discover_action_modules`)
2. Optionally walks the custom actions directory
3. Logs `INFO "Action loader initialized: N actions available"`

There is no caching at the engine level.  The loader is stateless after
discovery (its `_class_cache` is local to each throwaway instance, so even the
lazy-load cache inside `load_action_class` never warms up across calls).

Observed symptoms:
- Logs flooded at ~500 ms intervals (one entry per active machine per loop tick)
- `last_event` on 12 active tasks grows from 21 s → 46 s+ between log lines
- Actual `call_started`, `speech_recognized`, and error events cannot be found

## Proposed Solution

**A module-level cache keyed on `actions_root` already exists** (`_loader_instance` /
`get_action_loader()`, lines 277–285 of `action_loader.py`). It was never wired to
the engine. The fix is to complete that infrastructure, not invent a new one.

### Step 1 — Extend `get_action_loader` to cache by `actions_root`

```python
# action_loader.py
_loader_cache: dict[str | None, "ActionLoader"] = {}

def get_action_loader(actions_root: str | None = None) -> "ActionLoader":
    """Return a cached ActionLoader for the given actions_root."""
    if actions_root not in _loader_cache:
        _loader_cache[actions_root] = ActionLoader(actions_root=actions_root)
    return _loader_cache[actions_root]
```

Remove the old `_loader_instance` / `_loader_instance = None` variables.

### Step 2 — Wire engine to use `get_action_loader`

```python
# engine.py  _execute_pluggable_action  (replaces the 3-line inline instantiation)
from .action_loader import get_action_loader
loader = get_action_loader(self.actions_root)
action_class = loader.load_action_class(action_type)
```

### Step 3 — Downgrade the "initialized" log (separate commit)

```python
# action_loader.py  _discover_action_modules
logger.debug(          # was logger.info
    f"Action loader initialized: ..."
)
```

> Do **not** implement Option A (engine-level `self._action_loader`). It adds a
> new pattern alongside existing infrastructure and makes no difference when the
> cache is at module level.

## Acceptance Criteria

- [ ] `get_action_loader(actions_root)` caches by `actions_root` key; calling it
      twice with the same key returns the **same object** (`is` check)
- [ ] `_execute_pluggable_action` calls `get_action_loader(self.actions_root)` —
      no inline `ActionLoader(...)` at the call site
- [ ] "Action loader initialized" is `DEBUG`, not `INFO`
- [ ] `ActionLoader.__init__` (and therefore `_discover_action_modules`) is called
      exactly **once** for N sequential action executions on a single engine
      instance (new regression test in `tests/test_action_loader.py`)
- [ ] All existing tests in `tests/test_action_loader.py` and
      `tests/test_multiple_engines.py` pass — verify that `test_multiple_engines`
      patch targets still work after the change (update patch path if needed)
- [ ] Two separate commits: (1) DEBUG log change, (2) caching change

## Judgement Notes

- **Option A rejected**: engine-level `self._action_loader` is redundant — module
  cache is simpler and already scaffolded.
- **"last_event growth rate" criterion removed**: not automatable; covered
  implicitly by the init-call-count regression test.
- **Thread-safety**: module-level dict is safe for single-process async engines;
  no lock needed.
- **Test patch risk**: `test_multiple_engines.py` patches `ActionLoader` at its
  import path. If the patch target moves, those tests silently pass through. Must
  be verified and updated as part of this change.

## Related

- `src/statemachine_engine/core/engine.py` lines ~987–1002 (`_execute_pluggable_action`)
- `src/statemachine_engine/core/action_loader.py` lines ~113–121 (`_discover_action_modules`)
- FR-FSM-007 (engine split) — any refactor must keep the loader lifetime tied to
  the engine instance, not the call site
