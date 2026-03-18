# Feature Request: FR-FSM-011 Completed Action Indices Cross-State Leak

**Priority:** HIGH
**Type:** Bug
**Status:** Enforced ✅
**Effort:** 0.5 day
**Requested:** 2026-03-18

## Summary

`_completed_action_indices` leaks index 0 from a transition-triggering action
in state A into state B, causing state B's first action to be silently skipped.

## Value Statement

FSM authors get reliable action execution on state entry — actions fire when
the state machine enters a state, regardless of which action index triggered
the transition in the previous state.

## Problem

FR-FSM-009 introduced `_completed_action_indices` to prevent re-execution of
transition-triggering actions. The guard works correctly within a single state,
but has a cross-state contamination bug in the post-transition path.

### Root Cause

In `engine.py`, `_execute_state_actions()` lines 866-868:

```python
# RUNTIME DETECTION: mark action as completed if it triggered a transition
if self._state_entry_gen != entry_gen:
    self._completed_action_indices.add(idx)      # ← line 868: THE BUG
    continue
```

The execution sequence when action at index 0 in state A triggers a transition:

1. `_execute_state_actions()` runs for state A
2. Action at idx=0 returns an event (e.g., `"warmed"`)
3. `_execute_pluggable_action()` calls `process_event("warmed")`
4. `process_event()` transitions to state B:
   - Line 505: `self._completed_action_indices = set()`  ← **correctly cleared**
5. Control returns to `_execute_state_actions()` loop body (line 867)
6. Guard detects `_state_entry_gen != entry_gen` (True — state changed)
7. Line 868: `self._completed_action_indices.add(0)`  ← **CONTAMINATES state B**
8. Loop breaks (line 854 guard on next iteration)
9. Main loop calls `_execute_state_actions()` for state B
10. State B's action at idx=0: **SKIPPED** because `0 in _completed_action_indices`

### Reproducible Scenario

```yaml
states:
  - warming_up
  - connecting_ninchat
  - speaking_greeting

actions:
  warming_up:
    - type: yamlgraph_preload    # idx=0, returns "warmed"
      params:
        success: warmed

  connecting_ninchat:
    - type: ninchat_connect      # idx=0, NEVER EXECUTES
      params:
        success: ninchat_ready

transitions:
  - { from: warming_up, to: connecting_ninchat, event: warmed }
  - { from: connecting_ninchat, to: speaking_greeting, event: ninchat_ready }
```

Engine enters `connecting_ninchat` but `ninchat_connect` is never invoked.
The 30s timeout fires instead → transitions to `error`.

### Observed Impact

7 tests fail in `ninchat_voice/tests/test_nc142a_coordinator_transitions.py`:
all stuck at `connecting_ninchat` because `ninchat_connect` action is skipped.

```
FAILED TestFullDialogueLoop::test_full_dialogue_loop_transitions
  AssertionError: Timeout waiting for state='speaking_response'; current='connecting_ninchat'
```

Also affects `test_nc144_coordinator_mode_split.py::test_simple_mode_ignores_transcribed_in_forwarding` (same pattern).

### Debug Evidence

```
DEBUG  Loaded: yamlgraph_preload
INFO   warming_up --warmed--> connecting_ninchat: ninchat_connect
DEBUG  ⏰ Started timeout timeout(30) for state 'connecting_ninchat' -> 'error'
       # ← NO "Loaded: ninchat_connect" line ever appears
```

## Proposed Fix

Line 868 must NOT add to `_completed_action_indices` after a cross-state
transition has already cleared the set. Two options:

### Option A: Guard the add (minimal change)

```python
# Line 867-869 in _execute_state_actions()
if self._state_entry_gen != entry_gen:
    # Only mark completed if we're still in the SAME state entry
    # that the action was started in. If entry_gen changed, the set
    # was already cleared by process_event() — do not re-pollute it.
    break
```

Remove the `add(idx)` entirely — the action already completed by triggering
the transition; it's the old state's index, irrelevant to the new state.

### Option B: Snapshot and restore (defensive)

```python
entry_gen = self._state_entry_gen
saved_completed = self._completed_action_indices.copy()

for idx, action_config in enumerate(state_actions):
    if self._state_entry_gen != entry_gen:
        break  # state changed — stop processing old state's actions
    ...
```

### Recommendation

Option A — the `add(idx)` at line 868 serves no purpose. The transition
already happened; the old state's action index is meaningless for the new
state. A simple `break` without the `add` is correct and minimal.

## Acceptance Criteria

- [x] `_execute_state_actions()` does not add to `_completed_action_indices`
      after a cross-state transition
- [x] State B's idx=0 action executes after state A's idx=0 triggered the
      transition
- [x] Unit test: two-state chain where state A action triggers transition,
      state B action at same index fires
- [x] Unit test: three-state chain A→B→C all idx=0 fire
- [ ] All 7 `test_nc142a_coordinator_transitions.py` tests pass
- [ ] `test_nc144_coordinator_mode_split.py::test_simple_mode_ignores_transcribed_in_forwarding` passes
- [x] Existing FR-FSM-009 idempotency tests still pass (12/12)
- [x] FR-FSM-010 VB-006 non-transition one-shot semantics unchanged (407 passed)

## Alternatives Considered

- **Workaround in YAML**: Add a no-op `log` action at idx=0 in every state
  following a transition-triggering state. Fragile, non-obvious, violates the
  principle of least surprise.
- **Reset in main loop**: Clear `_completed_action_indices` before calling
  `_execute_state_actions()` when `_state_entry_gen` changed since last call.
  Also works but is less surgical than Option A.
