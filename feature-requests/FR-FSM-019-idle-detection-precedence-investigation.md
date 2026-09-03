# Feature Request: FR-FSM-019 Investigate idle-detection precedence in the main event loop

**Priority:** HIGH
**Type:** Investigation
**Status:** Proposed
**Effort:** 0.5–1 day
**Requested:** 2026-09-03

## Summary

`execute_state_machine()` computes `is_idle` with mixed `and`/`or` and
no grouping parentheses. Python binds `and` tighter than `or`, so the
expression evaluates as:

```
(current_state == "waiting" AND no _last_activity_time)
OR (has _last_activity_time AND stale > 5.0s)
```

The second disjunct ignores `current_state` entirely. Any machine that
has been quiet for >5s is classified idle **in every state**, dropping
the loop to 500ms ticks. The likely intended semantics is
`waiting AND (no activity OR stale activity)`.

## Code

`src/statemachine_engine/core/engine.py`, main event loop
(`execute_state_machine`):

```python
is_idle = (
    self.current_state == "waiting"
    and not hasattr(self, "_last_activity_time")
    or (
        hasattr(self, "_last_activity_time")
        and time.time() - self._last_activity_time > 5.0
    )
)

if is_idle:
    await asyncio.sleep(0.5)   # 500ms when idle
else:
    await asyncio.sleep(0.05)  # 50ms when active
```

`_check_control_socket()` runs once per loop iteration, so tick length
bounds the control-event pickup latency.

## Hypothesized impact

A machine parked in a **non-waiting** state awaiting an external event
(e.g. a voice coordinator waiting on `speak_done` / `transcribed` for
more than 5s of wall-clock silence) polls its control socket every
500ms instead of 50ms — up to ~500ms added latency on event receipt.
For latency-sensitive consumers (csap barge-in flows) this is a
material, hard-to-attribute delay that would present downstream as an
NC-shaped "slow to react" symptom with no engine-side error.

`_last_activity_time` is only refreshed on non-idle transitions
(`process_event`), so the stale branch arms easily during any long
listen/wait phase.

## Investigation plan (condemn before fixing)

1. **RED:** unit test that places a machine in a non-waiting state,
   ages `_last_activity_time` past 5s, and asserts the loop still
   selects the 50ms tick (fails today).
2. Measure actual event-pickup latency in both branches (timestamp a
   datagram send → `process_event` entry) to confirm the 500ms bound.
3. Check git history for the expression's origin — whether the
   precedence was ever intentional (CPU-saving during any quiet
   period) vs accidental.
4. Survey consumers for latency incidents that correlate (csap NC
   ledger: slow barge-in / delayed event pickup class).
5. **GREEN:** parenthesize to the intended semantics (or document the
   intentional behavior and rename `is_idle` accordingly).

## Related observation (secondary, same file)

Universal failure path routes exceptions to
`process_event("error")`; if the current state has no `error`
transition, `_find_transition` returns `None` and the failure is
swallowed with a DEBUG-level log. Consider WARN-level logging when an
error event finds no transition. Separate ticket if confirmed
worth fixing.

## Acceptance criteria

- AC-01: Failing test demonstrating the misclassification exists and
  is committed before any fix (RED).
- AC-02: Causal chain documented: expression → tick selection →
  event-pickup latency bound, with measured numbers.
- AC-03: Fix or explicit documented-as-intended disposition; if fixed,
  the RED test flips GREEN and guards regression.

## Provenance

Found during a cross-repo complexity evaluation (yamlgraph diary
2026-09-03 "the ledger files where the pain is"), reading engine.py
end-to-end. Filed from outside the repo; no code changed.
