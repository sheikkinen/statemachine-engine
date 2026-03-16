# FR-FSM-009: Action Idempotency Guard — Reflection

**Date:** 2026-03-16
**FR:** FR-FSM-009
**Commits:** `7869446` (RED), `5646c5f` (GREEN)
**Tests:** 7 new, 397 total (0 regressions)

## What happened

The main event loop calls `_execute_state_actions()` every 50–500ms tick.
All actions for the current state re-execute on every tick. Side-effecting
actions (`bash`, `send_event`, `start_fsm`) fire repeatedly — a latent bug
masked by the fact that most such actions trigger transitions within the
same tick, escaping the loop before the next iteration.

## Cognitive traps encountered

### 1. The "implicit synchronous guard" illusion

The original proposal stated: "The current code already handles this implicitly
because `process_event()` changes `self.current_state` synchronously."

This was wrong. `_execute_state_actions()` captures the action list at loop
start. Mid-loop state changes don't stop iteration — the captured list keeps
running. The mid-sequence abort (`_state_entry_gen` check + break) is the
**primary** fix, not an edge case.

**Trap name:** `downstream_fix` — the symptom (actions re-firing) was analyzed,
but the root cause (captured-list-continues-after-transition) was masked by
assuming synchronous semantics propagated through the loop.

### 2. The YAML-key heuristic fallacy

The first proposal detected one-shot actions by checking for `success`/`failure`
keys in YAML config. This ignores that all pluggable actions have code-level
defaults (`self.config.get("success", "job_done")`). A `bash` action without
`success:` in YAML still returns `"job_done"` and triggers a transition.

**Trap name:** `plausible_wrong_answer` — the heuristic passed shape-checking
(looks reasonable) but was semantically wrong. Runtime detection (observing
`_state_entry_gen` change) is both simpler and correct.

### 3. The self-loop reset trap

Resetting `_completed_action_indices` on self-loops would cause infinite
alternation: A1 fires → self-loop → reset → A1 fires again → repeat forever,
starving subsequent actions.

**Cure:** Only reset on transitions to a **different** state. Self-loops
increment the gen counter (for mid-sequence abort) but preserve the completed
set.

## Heuristic

**"Observe the change, don't predict the cause."** When guarding against
repeated execution, detect by observing the side effect (state changed) rather
than predicting which actions might cause it (YAML key presence). Runtime
detection is always more accurate than static heuristics for dynamic behavior.

## Seed

Can we apply the same pattern to `_check_control_socket`? If a control socket
event triggers `process_event` which transitions state mid-action-loop, the
current guard handles it. But what about the reverse — an action loop that
re-enters `_check_control_socket` indirectly via asyncio? Is there a reentrancy
risk in the main loop?
