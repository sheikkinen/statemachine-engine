# Diary: FR-FSM-011 — Completed Indices Cross-State Leak

**Date:** 2026-03-18
**FR:** FR-FSM-011
**Type:** Bug fix (TDD)

## What Happened

FR-FSM-009 introduced `_completed_action_indices` to prevent re-execution of
transition-triggering actions. The guard worked for self-loops but had a
cross-state contamination bug: after action[0] in state A triggered a
transition to state B, index 0 was added to the freshly-cleared set, causing
state B's action[0] to be silently skipped.

## The Fix

Two-character discrimination: `self.current_state == original_state`.

For self-loops (same state), the set is preserved by `process_event()` and the
index must be added. For cross-state transitions, the set was already cleared —
re-adding leaks old indices into the new state.

Also changed `continue` → `break` after the detection block. No reason to
continue iterating the old state's action list after detecting a transition.

## Cognitive Traps

### Stale Module Cache

The fix appeared to not work — tests still failed with the old behavior.
Root cause: the package was installed non-editable in the yamlgraph venv
(`site-packages/`), so `pytest` loaded the old `.py` file instead of the
edited source under `fsm/src/`. Fixed with `pip install -e ".[dev]"`.

**Lesson:** When a code fix doesn't take effect, verify `__file__` on the
imported module before doubting the logic.

### Option A Was Incomplete

The FR proposed "just remove the `add(idx)` and `break`" (Option A). During
investigation I caught that this would break the self-loop case: without the
`add`, a one-shot action would re-fire on every tick after a self-loop.

The correct fix required discriminating self-loop vs cross-state by comparing
`self.current_state` against a captured `original_state`.

**Lesson:** A "minimal change" proposal requires full case analysis. The
simplest-looking diff is not always the correct one when two distinct
control-flow paths share the same code block.

## Seed

If `process_event()` committed the _completed_action_indices semantics
(clear vs preserve) as an explicit return value rather than relying on
side-effect ordering, would the cross-state leak have been structurally
impossible? Consider a `TransitionResult` dataclass that encodes the
clearing policy.
