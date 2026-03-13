# Feature Request: validate.py Thin Wrapper

**Priority:** MEDIUM
**Type:** Enhancement
**Status:** Proposed
**Effort:** 0.5 days
**Requested:** 2026-03-13

## Summary

Replace the 512-line `tools/validate.py` with a thin wrapper that delegates
to `tools/linter/` using `--select` for the original 8 check codes.

## Value Statement

Eliminates 450+ lines of duplicated validation logic while preserving the
existing `statemachine-validate` CLI interface for users and scripts.

## Problem

`validate.py` (512 lines) and `tools/linter/` now implement overlapping
checks. The FR-FSM-001 acceptance criteria states: "After the linter ships,
`validate.py` becomes a thin wrapper calling `lint_config()` with `--select`
for its original checks, preserving the existing CLI interface."

| validate.py check | Linter equivalent |
|---|---|
| `_check_initial_state` | E001 |
| `_check_missing_events` | E003 |
| `_check_event_coverage` | W007 |
| `_check_action_emissions` | E009 |
| `_check_standard_patterns` | E010 |
| `_check_orphaned_states` | W001 |
| `_check_unreachable_states` | W001 |
| `_check_wildcard_transitions` | W003 |

## Proposed Solution

```python
# tools/validate.py — thin wrapper (~50 lines)
"""Backward-compatible wrapper around the graph linter."""

from statemachine_engine.tools.linter import lint_config
from statemachine_engine.tools.linter.models import Severity

LEGACY_CODES = {"E001", "E003", "E009", "E010", "W001", "W003", "W007"}

def main():
    # Parse args (same interface: files, --strict, --quiet)
    # Call lint_config() for each file
    # Filter to LEGACY_CODES
    # Format output in original style
```

### Migration path
1. Implement thin wrapper with identical CLI output
2. Run both old and new on all configs, diff output
3. Replace old with new once output matches
4. Remove old check methods

## Acceptance Criteria

- [ ] `statemachine-validate` CLI produces equivalent output to current version
- [ ] `--strict` and `--quiet` flags preserved
- [ ] Exit codes preserved (0 = clean, 1 = errors, 2 = warnings in strict)
- [ ] validate.py reduced from 512 lines to < 80 lines
- [ ] All existing validate tests pass (or are migrated to linter tests)
- [ ] pyproject.toml entry point unchanged

## Alternatives Considered

**Keep both independently:** Rejected — maintains 512 lines of duplicate
logic that will drift from the linter over time.

**Delete validate.py entirely:** Rejected — `statemachine-validate` is the
established CLI; users and scripts depend on it.

## Related

- FR-FSM-001 — Graph linter (acceptance criteria requires this)
- `tools/validate.py` — current 512-line implementation
- `tools/linter/` — replacement implementation
