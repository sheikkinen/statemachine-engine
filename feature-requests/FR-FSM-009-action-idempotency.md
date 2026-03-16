# Feature Request: Action Execution Idempotency Guard

**Priority:** HIGH
**Type:** Bug
**Status:** Proposed
**Effort:** 1 day
**Requested:** 2026-03-16

## Summary

Guard `_execute_state_actions()` so that side-effecting actions (those with
`success`/`failure` emission fields) run exactly once per state entry, while
polling actions (no emission fields) continue to run every tick.

## Value Statement

FSM authors get correct-by-default execution semantics — side-effecting
actions run once, polling actions repeat — eliminating a class of bugs
where `bash`, `send_event`, `start_fsm`, or `add_to_list` actions fire
repeatedly on every 50ms–500ms tick.

## Problem

`_execute_state_actions()` is called **every iteration of the main event loop**
(line 377), not just on state entry. This means ALL actions for the current
state re-execute every 50ms–500ms.

### Impact by action type

| Action | Re-fire safe? | Impact of repeated execution |
|--------|--------------|------------------------------|
| `log` | Mitigated | Rate-limited via `_log_count` |
| `sleep` | Mitigated | Counter-tracked, emits `wake_up` |
| `check_database_queue` | ✅ Yes | Designed for polling |
| `check_machine_state` | ✅ Yes | Read-only check |
| `set_context` | ✅ Yes | Idempotent overwrite |
| `bash` | ❌ **NO** | Re-runs shell command, duplicates side effects |
| `send_event` | ❌ **NO** | Re-sends event to target machine |
| `complete_job` | ❌ **NO** | Re-completes job in DB |
| `start_fsm` | ❌ **NO** | Spawns new FSM subprocess every tick |
| `add_to_list` | ❌ **NO** | Appends duplicate entries |
| `pop_from_list` | ⚠️ Semi | Empties list progressively |
| `claim_job` | ⚠️ Semi | Second claim fails (DB constraint) |

### Why it hasn't been catastrophic (yet)

Side-effecting actions typically have `success`/`failure` fields that emit an
event causing a state transition within the same tick. The action runs, emits
`job_done`, the engine transitions to another state, and the next tick executes
that new state's actions instead. But if event processing is slow, the
transition race is lost, or the event fails to find a valid transition, the
action re-fires.

### Observed in practice

The `controller.yaml` example has `send_event` actions that could re-fire.
The `concurrent-controller.yaml` has `start_fsm` actions that could spawn
duplicate workers. The `patient-records.yaml` has `complete_job` that could
double-complete.

## Proposed Solution

### Design: "emit = run-once" semantic

The natural invariant: **actions with `success`/`failure`/`error` emission
fields are one-shot per state entry**. Actions without emission fields are
polling/stateless and safe to repeat.

### Implementation

Add a `_state_entry_generation` counter and `_completed_action_indices` set
to the engine:

```python
class StateMachineEngine:
    def __init__(self, ...):
        ...
        self._state_entry_gen = 0          # Incremented on each state entry
        self._completed_action_indices = set()  # Reset on state entry

    async def process_event(self, event, context=None):
        ...
        if new_state:
            previous_state = self.current_state
            self.current_state = new_state
            # Reset action tracking on state entry
            self._state_entry_gen += 1
            self._completed_action_indices = set()
            ...

    async def _execute_state_actions(self):
        self.context["current_state"] = self.current_state
        state_actions = self.config.get("actions", {}).get(self.current_state, [])

        for idx, action_config in enumerate(state_actions):
            # Skip one-shot actions that already completed in this state entry
            if idx in self._completed_action_indices:
                continue

            is_one_shot = any(
                k in action_config for k in ("success", "failure", "error")
            )

            await self._execute_action(action_config)
            self._propagate_job_context()

            # Mark one-shot actions as completed
            if is_one_shot:
                self._completed_action_indices.add(idx)
```

### Why this works

1. **Polling actions** (`check_database_queue`, `log`, `sleep`) have no
   `success`/`failure` fields → re-execute every tick as before
2. **Side-effecting actions** (`bash`, `send_event`, `start_fsm`) have
   `success`/`failure` → execute once, skip on subsequent ticks
3. **State transitions reset the tracker** → actions run fresh on re-entry
4. **Self-loops** (`from: waiting, to: waiting`) increment the generation
   counter → actions re-execute on self-transition (correct behavior)
5. **No config changes needed** — existing YAML configs work unchanged

### Edge case: action emits event mid-sequence

When a one-shot action emits an event that triggers a transition, the remaining
actions in the sequence should NOT execute (the state has changed). The current
code already handles this implicitly because `process_event()` changes
`self.current_state` synchronously. But we should add a guard:

```python
    current_gen = self._state_entry_gen
    for idx, action_config in enumerate(state_actions):
        if self._state_entry_gen != current_gen:
            break  # State changed mid-sequence, abort remaining actions
        ...
```

### Linter integration

Add a new warning to FR-FSM-001's action checks:

```
W011  warning  Side-effecting action (bash/send_event/start_fsm/add_to_list)
               without success/failure field — will re-fire every tick
```

This catches the case where an author writes a `bash` action without a
`success` event, which would run the command repeatedly.

## Acceptance Criteria

- [ ] `_state_entry_gen` counter + `_completed_action_indices` set added
- [ ] One-shot detection: actions with `success`/`failure`/`error` run once
- [ ] Polling actions (no emission) continue to repeat every tick
- [ ] State transitions (including self-loops) reset the tracker
- [ ] Mid-sequence state change aborts remaining actions
- [ ] No behavioral change for correctly-configured machines
- [ ] Unit test: bash action with success runs once per state entry
- [ ] Unit test: check_database_queue runs every tick
- [ ] Unit test: self-loop resets action completion
- [ ] Unit test: mid-sequence transition aborts remaining actions
- [ ] W011 linter warning added for unguarded side-effecting actions
- [ ] All 390 existing tests pass

## Alternatives Considered

**Execute on state entry only (skip if state unchanged):** Rejected — breaks
polling patterns (`check_database_queue` in `waiting` state must repeat).

**Action-level `run_once: true` flag:** Rejected — requires config changes to
all existing YAML files and is easy to forget. The `success`/`failure`
presence is a natural semantic marker.

**Track by action hash instead of index:** Considered — would handle dynamic
action lists, but FSM configs are static. Index is simpler and sufficient.

**asyncio.Lock around action execution:** Rejected — adds concurrency
complexity for a fundamentally sequential loop.

## Related

- FR-FSM-001 — Graph linter (W011 addition)
- FR-FSM-007 — Split engine.py (this change increases motivation to split)
- `core/engine.py` lines 377, 822–833, 401–493
