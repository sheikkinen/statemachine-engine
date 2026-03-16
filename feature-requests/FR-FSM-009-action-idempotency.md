# Feature Request: Action Execution Idempotency Guard

**Priority:** HIGH
**Type:** Bug
**Status:** Enforced ✅
**Effort:** 1 day
**Requested:** 2026-03-16
**Judged:** 2026-03-16

## Summary

Guard `_execute_state_actions()` so that actions which trigger state
transitions run exactly once per state entry, while polling actions
(those that don't trigger transitions) continue to run every tick.
Detection is runtime-based: if an action caused `_state_entry_gen` to
change, it is marked completed and skipped on subsequent ticks.

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

### Design: Runtime transition detection

The natural invariant: **actions that trigger state transitions are one-shot
per state entry**. Actions that don't trigger transitions are polling/stateless
and safe to repeat. Detection is runtime-based — no YAML-key heuristic needed.

All pluggable actions return events via code-level defaults (e.g. `bash_action`
always returns `self.config.get("success", "job_done")`), so checking for
`success`/`failure`/`error` keys in YAML is unreliable. Instead, we observe
whether `_state_entry_gen` changed after executing each action.

### Implementation

Add a `_state_entry_gen` counter and `_completed_action_indices` set to the
engine:

```python
class StateMachineEngine:
    def __init__(self, ...):
        ...
        self._state_entry_gen = 0               # Incremented on each state transition
        self._completed_action_indices = set()   # Reset on transitions to different state

    async def process_event(self, event, context=None):
        ...
        if new_state:
            previous_state = self.current_state
            self.current_state = new_state
            self._state_entry_gen += 1
            # Only reset completed actions on transitions to a DIFFERENT state.
            # Self-loops preserve the set to prevent infinite re-fire.
            if new_state != previous_state:
                self._completed_action_indices = set()
            ...

    async def _execute_state_actions(self) -> None:
        self.context["current_state"] = self.current_state
        state_actions = self.config.get("actions", {}).get(self.current_state, [])
        entry_gen = self._state_entry_gen

        for idx, action_config in enumerate(state_actions):
            # PRIMARY GUARD: abort if state changed mid-sequence.
            # The action list was captured at loop start — without this check,
            # remaining actions execute even after a transition.
            if self._state_entry_gen != entry_gen:
                break

            # Skip actions that already triggered transitions in this state entry
            if idx in self._completed_action_indices:
                continue

            await self._execute_action(action_config)
            self._propagate_job_context()

            # RUNTIME DETECTION: if this action triggered a state change,
            # mark it as completed so it won't re-fire on subsequent ticks
            if self._state_entry_gen != entry_gen:
                self._completed_action_indices.add(idx)
```

### Why this works

1. **Mid-sequence abort** — the `entry_gen` check breaks the loop when an
   action triggers a transition, preventing remaining captured actions from
   executing in the wrong state. This is the primary bug fix.
2. **Runtime one-shot detection** — polling actions (`wait_for_jobs` returning
   `None`, `check_database_queue`) never trigger transitions → never marked →
   repeat every tick. Side-effecting actions (`bash`, `send_event`) trigger
   transitions → marked → run once.
3. **Self-loops preserve completed set** — `_completed_action_indices` is NOT
   reset on self-loops, preventing infinite alternation where A1 fires, causes
   self-loop, resets, A1 fires again, forever starving A2/A3.
4. **Different-state transitions reset** — entering a genuinely new state
   clears the completed set, allowing all actions to run fresh.
5. **No config changes needed** — existing YAML configs work unchanged.
6. **No YAML-key heuristic** — works correctly even for actions that omit
   `success:`/`failure:` in YAML but return events via code defaults.

## Acceptance Criteria

- [ ] `_state_entry_gen` counter + `_completed_action_indices` set initialized in `__init__`
- [ ] Mid-sequence abort: loop breaks when `_state_entry_gen` changes during iteration
- [ ] Runtime one-shot detection: actions that triggered transitions are marked completed
- [ ] Polling actions (no transition triggered) repeat every tick
- [ ] State transitions to different state reset `_completed_action_indices`
- [ ] Self-loops increment gen counter but do NOT reset completed set
- [ ] No behavioral change for correctly-configured machines
- [ ] Unit test: bash action causing transition runs once per state entry
- [ ] Unit test: check_database_queue (returns None) runs every tick
- [ ] Unit test: self-loop preserves completed actions (no infinite alternation)
- [ ] Unit test: mid-sequence transition aborts remaining actions
- [ ] Unit test: re-entry from different state resets completed set
- [ ] All existing tests pass (390+)

## Alternatives Considered

**Execute on state entry only (skip if state unchanged):** Rejected — breaks
polling patterns (`check_database_queue` in `waiting` state must repeat).

**Action-level `run_once: true` flag:** Rejected — requires config changes to
all existing YAML files and is easy to forget.

**YAML-key heuristic (`success`/`failure`/`error` presence):** Rejected —
all pluggable actions return events via code-level defaults regardless of
YAML presence (e.g. `bash_action` always returns `"job_done"`). A `bash`
action WITHOUT `success:` in YAML is equally dangerous. Runtime detection
(observing whether `_state_entry_gen` changed) is both simpler and correct.

**Track by action hash instead of index:** Considered — would handle dynamic
action lists, but FSM configs are static. Index is simpler and sufficient.

**asyncio.Lock around action execution:** Rejected — adds concurrency
complexity for a fundamentally sequential loop.

## Related

- FR-FSM-007 — Split engine.py (this change increases motivation to split)
- FR-FSM-010 (future) — W011 linter warning for unguarded side-effecting actions
- `core/engine.py` lines 377, 822–833, 401–493

---

## Judgement (2026-03-16)

**Verdict: APPROVED with 5 mandatory amendments.**

The problem identification is accurate and well-documented. The impact table and
"why it hasn't been catastrophic" analysis are excellent. However, the proposed
solution has a **flawed detection heuristic** and mischaracterizes the primary
fix as an edge case.

### Amendment 1: CRITICAL — Mid-sequence abort is the PRIMARY fix, not an edge case

The FR states: "The current code already handles this implicitly because
`process_event()` changes `self.current_state` synchronously."

**This is wrong.** `_execute_state_actions()` captures the action list at the
START of the method:

```python
state_actions = self.config.get("actions", {}).get(self.current_state, [])
for action_config in state_actions:
    await self._execute_action(action_config)
```

The loop iterates ALL captured actions even after `self.current_state` changes
mid-loop. An action at index 0 that triggers a transition does NOT prevent
actions 1, 2, … from executing — they were already fetched.

**Fix:** The mid-sequence abort (`_state_entry_gen` check + `break`) must be the
primary mechanism, not an afterthought. Promote it from "Edge case" subsection
to the main Implementation section.

### Amendment 2: CRITICAL — Replace YAML-key heuristic with runtime detection

The proposed one-shot detection checks YAML config keys:
```python
is_one_shot = any(k in action_config for k in ("success", "failure", "error"))
```

**This is unreliable.** All pluggable actions return events via code-level
defaults regardless of YAML presence:

| Action | No YAML `success:` | Returns |
|--------|---------------------|---------|
| `bash_action` | `self.config.get("success", "job_done")` | Always `"job_done"` |
| `set_context_action` | `self.config.get("success", "success")` | Always `"success"` |
| `log_action` | `self.config.get("success", "continue")` | Always `"continue"` |

A `bash` action WITHOUT `success:` in YAML is EQUALLY dangerous — it still runs
and returns `"job_done"`, but the heuristic wouldn't detect it as one-shot.

**Fix:** Detect one-shot by runtime behavior, not YAML keys. If executing an
action changed `_state_entry_gen` (meaning it triggered a transition), mark it
as completed. This is both simpler and correct:

```python
async def _execute_state_actions(self) -> None:
    self.context["current_state"] = self.current_state
    state_actions = self.config.get("actions", {}).get(self.current_state, [])
    entry_gen = self._state_entry_gen

    for idx, action_config in enumerate(state_actions):
        # Abort if state changed mid-sequence
        if self._state_entry_gen != entry_gen:
            break

        # Skip actions that already triggered transitions in this entry
        if idx in self._completed_action_indices:
            continue

        await self._execute_action(action_config)
        self._propagate_job_context()

        # If this action triggered a state change, mark it as completed
        if self._state_entry_gen != entry_gen:
            self._completed_action_indices.add(idx)
```

**Why this is better:** Polling actions (e.g., `wait_for_jobs` returning `None`,
or `check_database_queue`) never trigger transitions → never marked → repeat
every tick. Side-effecting actions trigger transitions → marked → run once.
No YAML-level heuristic needed.

### Amendment 3: Don't reset tracker on self-loops

The FR says: "Self-loops increment the generation counter → actions re-execute
on self-transition (correct behavior)."

**This causes an infinite alternation bug.** Consider state `S` with actions
A1 (one-shot), A2 (one-shot), A3 (poll):

1. Tick 1: A1 runs → self-loop → gen increments → `completed = {}` reset → A1 marked → break
2. Tick 2: A1 in completed (still {0} from step 1? No — reset in step 1)

With reset-on-self-loop: `completed` was cleared, A1 runs AGAIN, causes
another self-loop, ad infinitum. A2 and A3 never execute.

**Fix:** Only reset `_completed_action_indices` on transitions to a DIFFERENT
state. Self-loops preserve the completed set:

```python
async def process_event(self, event, context=None):
    ...
    if new_state:
        previous_state = self.current_state
        self.current_state = new_state
        self._state_entry_gen += 1
        # Only reset completed actions on actual state change
        if new_state != previous_state:
            self._completed_action_indices = set()
        ...
```

Self-loops still increment the gen counter (needed for mid-sequence abort),
but completed actions remain marked, preventing re-fire.

### Amendment 4: Defer W011 linter warning to separate scope

Mixing an engine runtime fix with a linter extension violates single-concern
commits. The W011 warning is valuable but should be:

- Filed as an addendum to FR-FSM-002 or a separate FR-FSM-010
- Not an acceptance criterion for this FR
- Implemented after the engine fix is stable

**Fix:** Remove W011 from this FR's acceptance criteria. The engine
idempotency guard is the deliverable.

### Amendment 5: Update acceptance criteria for revised design

Replace the current acceptance criteria with:

- [ ] `_state_entry_gen` counter + `_completed_action_indices` set initialized in `__init__`
- [ ] Mid-sequence abort: loop breaks when `_state_entry_gen` changes during iteration
- [ ] Runtime one-shot detection: actions that triggered transitions are marked completed
- [ ] Polling actions (no transition triggered) repeat every tick
- [ ] State transitions to different state reset `_completed_action_indices`
- [ ] Self-loops increment gen counter but do NOT reset completed set
- [ ] No behavioral change for correctly-configured machines
- [ ] Unit test: bash action causing transition runs once per state entry
- [ ] Unit test: check_database_queue (returns None) runs every tick
- [ ] Unit test: self-loop preserves completed actions (no infinite alternation)
- [ ] Unit test: mid-sequence transition aborts remaining actions
- [ ] Unit test: re-entry from different state resets completed set
- [ ] All existing tests pass (390+)
