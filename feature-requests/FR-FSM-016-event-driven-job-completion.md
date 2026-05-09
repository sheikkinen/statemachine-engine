# Feature Request: Event-Driven Job Completion (Replace Polling)

**Priority:** LOW
**Type:** Enhancement
**Status:** Proposed
**Effort:** 2 days
**Requested:** 2026-05-09
**Origin:** NC-281 cross-reference — ninchat_voice FREE signal pattern

## Summary

Replace the `wait_for_jobs` 2-second database poll loop with a push-based listener on the event socket. Workers already emit `state_change` events when reaching terminal states — the controller can listen for those instead of querying the database in a busy loop.

## Value Statement

Controller FSMs detect worker completion instantly (0ms vs up to 2s latency), reducing batch turnaround time and eliminating unnecessary database queries.

## Problem

`WaitForJobsAction` polls the database every N seconds:

```python
# Current: poll loop in wait_for_jobs_action.py
# Controller sits in waiting_for_batch, engine fires timeout(2),
# re-enters the state, action queries DB, repeat until all done.
```

This works but has two costs:
1. **Latency:** Up to 2s delay between worker completion and controller awareness
2. **Database load:** One `SELECT ... WHERE job_id IN (...)` query every 2 seconds per batch

Meanwhile, every worker FSM already emits `state_change` events to `/tmp/statemachine-events.sock` when transitioning to terminal states. This data stream is unused by the controller.

## Proposed Solution

New action: `wait_for_events` — listens on Unix DGRAM socket for worker state transitions.

```yaml
# Controller YAML
actions:
  waiting_for_batch:
    - type: wait_for_events
      event_socket_path: "/tmp/statemachine-events.sock"
      tracked_machines_key: "spawned_machine_names"   # context key with list of machine names
      terminal_states: ["ready", "failed", "shutdown"] # states that count as "done"
      timeout: 300
      success: all_workers_done
      timeout_event: check_timeout
```

Implementation sketch:

```python
class WaitForEventsAction(BaseAction):
    """Listen on event socket for worker terminal state transitions."""

    async def execute(self, context: dict[str, Any]) -> str:
        machine_names = set(context.get(self.tracked_machines_key, []))
        done = set()

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.bind(f"/tmp/controller-listener-{os.getpid()}.sock")
        # ... subscribe to event socket or receive datagrams
        # When state_change for a tracked machine with terminal state arrives:
        #   done.add(machine_name)
        # When done == machine_names: return success
```

**Alternative (simpler):** Keep the existing `wait_for_jobs` DB poll but add an `event_shortcut` option — if a `state_change` event arrives on the socket for a tracked machine in a terminal state, skip the poll timer and query the DB immediately. This preserves the DB as source of truth while cutting latency.

## Acceptance Criteria

- [ ] Controller detects worker completion within 100ms (vs current 2s)
- [ ] Database remains source of truth for job status (event is a hint, DB is the confirmation)
- [ ] Graceful fallback: if event socket unavailable, fall back to poll mode
- [ ] Works with existing `start_fsm` action — no changes to worker side
- [ ] Tests: mock event socket, verify instant detection vs poll baseline

## Alternatives Considered

| Approach | Status |
|----------|--------|
| Current poll loop | Works, 2s latency, acceptable for demos |
| Pure socket listener (no DB) | Risky — lost datagram = stuck controller |
| Hybrid: socket hint + DB confirm | **Preferred** — best of both |

## Related

- `src/statemachine_engine/actions/builtin/wait_for_jobs_action.py` — current poll implementation
- `src/statemachine_engine/core/engine.py` — `EventSocketManager` (worker emits here)
- `projects/ninchat_voice/docs/NC-280-supervisor-fork.md` — FREE datagram pattern (origin)
- `projects/ninchat_voice/docs/NC-281-supervisor-monitoring.md` — cross-reference
- `docs/parallel-state-machines.md` — documents the poll pattern and notes push as future enhancement
