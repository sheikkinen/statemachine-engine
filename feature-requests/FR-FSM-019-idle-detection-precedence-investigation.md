# Feature Request: FR-FSM-019 Investigate idle-detection precedence in the main event loop

**Priority:** HIGH
**Type:** Investigation
**Status:** Implemented (2026-09-04, branch `fr-fsm-019-idle-precedence`)
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

## Findings (2026-09-04)

**Origin (plan step 3).** Expression unchanged since initial commit
`6a97041` (2025-10-07); only touched by a ruff-format pass. The
accompanying comment already read "Idle = in waiting state with no
recent activity" — intent was `waiting AND (...)`; the precedence was
accidental, not a CPU-saving design.

**Causal chain (AC-02).** `execute_state_machine()` calls
`_check_control_socket()` once per iteration, then sleeps `0.5` or
`0.05`. A datagram arriving mid-sleep waits for the remainder of the
tick, so pickup latency is uniform on `[0, tick]`. Measured with
`tmp/fr019_latency.py` (real control socket, state `listening`,
self-loop on `ping`, `_last_activity_time` aged 10s before each of 40
sends, jittered send phase):

| branch | p50 | p90 | max |
|---|---|---|---|
| before fix, stale non-waiting | 216 ms | 454 ms | 476 ms |
| before fix, fresh non-waiting | 19 ms | 28 ms | 47 ms |
| after fix, stale non-waiting | 18 ms | 27 ms | 33 ms |

The 500ms bound is confirmed; the fix removes it for every
non-`waiting` state.

**Consumer survey (plan step 4).** Not performed — csap NC ledger is
outside this repo. The measured 0–476ms window is the signature to grep
for if that survey is done.

**Related observation.** Not changed here; DEBUG-level swallow of
unmatched `error` events still stands. Separate ticket if wanted.

## Acceptance criteria

- [x] AC-01: `tests/core/test_idle_tick_precedence.py::test_non_waiting_state_keeps_active_tick_when_stale`
  committed RED in `fd0b9ca` (fails `0.5 == 0.05` on pre-fix code).
  Three companion tests pin the `waiting` semantics.
- [x] AC-02: Causal chain + measured numbers above.
- [x] AC-03: Fixed in `d95b1ed` — `is_idle = current_state == "waiting"
  and (no activity or stale)`. RED test flips GREEN; full suite 416
  passed / 9 skipped.

## Provenance

Found during a cross-repo complexity evaluation (yamlgraph diary
2026-09-03 "the ledger files where the pain is"), reading engine.py
end-to-end. Filed from outside the repo; no code changed.
