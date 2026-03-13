# Feature Request: Split core/engine.py

**Priority:** MEDIUM
**Type:** Enhancement
**Status:** Proposed
**Effort:** 1.5 days
**Requested:** 2026-03-13

## Summary

Split `core/engine.py` (989 lines — 2.2x the 450-line limit) into focused
submodules: state management, action execution, event handling, and config
loading.

## Value Statement

The core engine becomes testable and navigable per concern — state transitions,
action execution, and event handling can be understood and modified independently.

## Problem

`core/engine.py` at 989 lines exceeds the 450-line limit by 2.2x. It is the
heart of the FSM framework, combining:
- Config loading and validation
- State transition logic
- Action execution orchestration
- Event handling and dispatch
- Context management (including NC-120 context_map)
- EventSocketManager integration
- Terminal state detection
- Loop protection

This coupling makes it difficult to test individual concerns and increases the
risk of unintended side effects when modifying any part.

## Proposed Solution

Split into a `core/engine/` package:

```
core/engine/__init__.py         → StateMachineEngine class (facade, ~150 lines)
core/engine/state.py            → State transition logic, terminal detection
core/engine/executor.py         → Action execution orchestration
core/engine/events.py           → Event handling, dispatch, EventSocketManager
core/engine/config.py           → Config loading, context_map building
core/engine/context.py          → Context management, interpolation
```

The `StateMachineEngine` class in `__init__.py` becomes a thin facade
delegating to the submodules. Public API unchanged.

## Acceptance Criteria

- [ ] `core/engine.py` replaced by `core/engine/` package
- [ ] All submodules < 400 lines
- [ ] `StateMachineEngine` public API unchanged
- [ ] All 390 existing tests pass
- [ ] Pre-commit file-size-gate exclusion for `core/engine.py` removed
- [ ] Interpolation regex, terminal states, and context_map logic preserved exactly

## Alternatives Considered

**Extract only config loading:** Insufficient — even without config loading,
the remaining engine code exceeds 450 lines.

**Mixin classes:** Rejected — mixins obscure the dependency graph and make
testing harder. Composition via submodules is clearer.

## Related

- FR-186 — Pre-commit quality gates (file-size-gate exempts this file)
- NC-120 — context_map (logic lives in engine.py)
- FR-FSM-001 — Linter references engine internals (terminal states, interpolation regex)
