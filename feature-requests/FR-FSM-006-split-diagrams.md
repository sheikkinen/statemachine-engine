# Feature Request: Split tools/diagrams.py

**Priority:** MEDIUM
**Type:** Enhancement
**Status:** Proposed
**Effort:** 1 day
**Requested:** 2026-03-13

## Summary

Split `tools/diagrams.py` (992 lines — 2.2x the 450-line limit) into focused
submodules by diagram type.

## Value Statement

Diagram generation code becomes modular — adding a new diagram format means
adding a new file, not extending a 992-line monolith.

## Problem

`tools/diagrams.py` at 992 lines exceeds the 450-line limit by 2.2x. It
combines Mermaid generation, ASCII rendering, SVG export, and CLI argument
handling in a single file, making it difficult to maintain or extend.

## Proposed Solution

Split into a `tools/diagrams/` package:

```
tools/diagrams/__init__.py      → public API + main() entry point (~60 lines)
tools/diagrams/mermaid.py       → Mermaid diagram generation
tools/diagrams/ascii.py         → ASCII/text diagram rendering
tools/diagrams/svg.py           → SVG export
tools/diagrams/cli.py           → CLI argument parsing and dispatch
```

## Acceptance Criteria

- [ ] `tools/diagrams.py` replaced by `tools/diagrams/` package
- [ ] All submodules < 400 lines
- [ ] `statemachine-fsm` and `statemachine-diagrams` CLI behavior unchanged
- [ ] All existing tests pass
- [ ] Pre-commit file-size-gate exclusion for `tools/diagrams.py` removed

## Alternatives Considered

**Keep as single file with regions:** Rejected — 992 lines is well past the
maintainability threshold; regions don't help with testing isolation.

## Related

- FR-186 — Pre-commit quality gates (file-size-gate exempts this file)
- `.pre-commit-config.yaml` — exclusion list to update
