# Feature Request: Split database/cli.py

**Priority:** HIGH
**Type:** Enhancement
**Status:** Proposed
**Effort:** 1 day
**Requested:** 2026-03-13

## Summary

Split `database/cli.py` (1,379 lines — 3x the 450-line limit) into focused
submodules by command group.

## Value Statement

Developers can navigate, test, and modify individual CLI command groups
independently instead of scrolling through a 1,379-line monolith.

## Problem

`database/cli.py` at 1,379 lines is the largest source file in the codebase,
exceeding the 450-line hard limit by 3x. It combines database CRUD operations,
migration commands, reporting, and utility functions in a single file. The
pre-commit file-size-gate currently excludes it.

## Proposed Solution

Split into a `database/cli/` package:

```
database/cli/__init__.py        → main() entry point, argument parser setup (~80 lines)
database/cli/commands_crud.py   → create, read, update, delete operations
database/cli/commands_query.py  → search, list, filter operations
database/cli/commands_admin.py  → migrate, backup, repair operations
database/cli/formatters.py      → output formatting (table, JSON, CSV)
```

Each module should be < 400 lines. The `__init__.py` registers subcommands
and delegates to the appropriate module.

## Acceptance Criteria

- [ ] `database/cli.py` replaced by `database/cli/` package
- [ ] All submodules < 400 lines
- [ ] `statemachine-db` CLI behavior unchanged
- [ ] All existing tests pass
- [ ] Pre-commit file-size-gate exclusion for `database/cli.py` removed
- [ ] No new dependencies

## Alternatives Considered

**Inline refactor within single file:** Rejected — even aggressive refactoring
can't get 1,379 lines under 450 without splitting responsibilities.

## Related

- FR-186 — Pre-commit quality gates (file-size-gate exempts this file)
- `.pre-commit-config.yaml` — exclusion list to update
