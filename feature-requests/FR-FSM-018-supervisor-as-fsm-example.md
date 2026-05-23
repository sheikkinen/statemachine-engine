# Feature Request: Supervisor-as-FSM Example

**Priority:** LOW
**Type:** Example / Documentation
**Status:** Proposed
**Effort:** 1 day
**Requested:** 2026-05-09
**Origin:** NC-281 cross-reference — ninchat_voice supervisor pool design

## Summary

Add `examples/supervisor/` — a runnable example where a controller FSM manages
a fixed-size pool of worker FSMs, tracks pool health, and models graceful
shutdown. The example demonstrates the "supervisor as a state machine" pattern:
the controller's state encodes pool intent (`accepting`, `draining`, `stopped`)
and transitions are driven by worker FSM lifecycle events rather than timers.

This is distinct from the existing `controller_worker` example, which uses a
DB job queue. The supervisor example uses a **fixed pool** (N workers always
running, not spawned per job) and **health-driven transitions**.

## Value Statement

Projects that need prefork-style process pools (web servers, voice call
handlers, GPU pipelines) get a documented, working FSM pattern rather than
re-inventing the supervisor design in application code.

## Problem

The existing `controller_worker` example covers the job-queue / queue-drain
pattern well. It does not cover the **fixed-pool / always-on** pattern:

| Concern | `controller_worker` | `supervisor` (this FR) |
|---------|---------------------|----------------------|
| Worker count | Dynamic (1 per job) | Fixed (N at startup) |
| Worker lifecycle | Spawn → run → done → gone | Spawn → loop forever → restart on crash |
| Controller state | `dispatching` / `waiting` / `done` | `accepting` / `pool_exhausted` / `draining` / `stopped` |
| Crash handling | Not modelled | Worker death → `worker_crash` event → respawn |
| Shutdown | Not modelled | Drain: wait for active workers before SIGTERM |

The ninchat_voice project (`NC-280` / `NC-281`) required this pattern for
Twilio call handling and was the first to implement it. The FSM design proved
clean and testable. This example graduates the insight.

## Proposed Solution

### File structure

```
examples/supervisor/
├── README.md
├── run.sh                        # start pool: supervisor + 3 workers + monitor
├── config/
│   ├── supervisor.yaml           # controller FSM (pool lifecycle)
│   └── worker.yaml               # worker FSM (single loop iteration)
└── actions/
    └── health_check_action.py    # custom action: query /machines/health
```

### `config/supervisor.yaml` — key states

```yaml
name: "Supervisor"
description: "Fixed-pool process supervisor FSM"
template: false          # No Kanban — single machine, use Mermaid tab

initial_state: starting

# === STATE GROUPS ===
states:
  # === STARTUP ===
  - starting
  - spawning_workers

  # === POOL RUNNING ===
  - accepting
  - pool_exhausted

  # === SHUTDOWN ===
  - draining
  - stopped

events:
  - pool_ready          # all N workers reached their ready state
  - capacity_available  # a slot opened (worker finished current task)
  - capacity_exhausted  # all slots in use
  - worker_crash        # a worker process exited unexpectedly
  - drain               # external signal: begin graceful shutdown
  - pool_empty          # all workers have stopped after drain
  - workers_spawned

transitions:
  - from: starting
    to: spawning_workers
    event: workers_spawned

  - from: spawning_workers
    to: accepting
    event: pool_ready

  - from: accepting
    to: pool_exhausted
    event: capacity_exhausted

  - from: pool_exhausted
    to: accepting
    event: capacity_available

  - from: [accepting, pool_exhausted]
    to: accepting
    event: worker_crash      # restart the crashed worker, stay operational

  - from: [accepting, pool_exhausted]
    to: draining
    event: drain

  - from: draining
    to: stopped
    event: pool_empty

actions:
  starting:
    - type: log
      message: "Supervisor starting — spawning {pool_size} workers"
    - type: start_fsm
      yaml_path: "config/worker.yaml"
      machine_name: "worker_001"
      store_pid: true
    - type: start_fsm
      yaml_path: "config/worker.yaml"
      machine_name: "worker_002"
      store_pid: true
    - type: start_fsm
      yaml_path: "config/worker.yaml"
      machine_name: "worker_003"
      store_pid: true
    - type: emit_event
      event: workers_spawned

  spawning_workers:
    - type: custom
      module: actions.health_check_action
      class: HealthCheckAction
      expected_machines: ["worker_001", "worker_002", "worker_003"]
      retry_interval: 1.0
      success: pool_ready
      timeout_event: worker_crash    # timeout here means spawn failed

  accepting:
    - type: log
      message: "Pool healthy — {active_workers}/{pool_size} active"
    - type: wait          # yield until next external event
      timeout: 30
      timeout_event: drain

  draining:
    - type: log
      message: "Draining — waiting for {active_workers} active workers"
    - type: wait_for_jobs
      expected_final_states: ["stopped"]
      success: pool_empty
      timeout: 120
      timeout_event: pool_empty    # force stop after timeout
```

### `config/worker.yaml` — key design

```yaml
name: "Worker"
template: true           # Kanban tab — multiple workers grouped by machine_name

initial_state: idle

states:
  # === LIFECYCLE ===
  - idle
  - busy
  - stopped

events:
  - work_available
  - work_done
  - stop

transitions:
  - from: idle
    to: busy
    event: work_available

  - from: busy
    to: idle
    event: work_done

  - from: "*"
    to: stopped
    event: stop

actions:
  idle:
    - type: log
      message: "Worker {machine_name} idle"
    - type: wait
      timeout: 5
      timeout_event: work_available    # simulate work arriving

  busy:
    - type: bash
      command: "sleep 2 && echo 'work done'"
      success: work_done
```

### `actions/health_check_action.py`

```python
"""
HealthCheckAction — polls GET /machines/health until all expected machines
are alive. Demonstrates the FR-FSM-017 endpoint as a first-class FSM action.
"""

import asyncio
import aiohttp
from statemachine_engine.actions.base import BaseAction


class HealthCheckAction(BaseAction):

    def __init__(self, config):
        super().__init__(config)
        self.expected_machines = config.get("expected_machines", [])
        self.retry_interval = config.get("retry_interval", 1.0)
        self.health_url = config.get(
            "health_url", "http://localhost:3002/machines/health"
        )
        self.max_attempts = config.get("max_attempts", 30)

    async def execute(self, context):
        for attempt in range(self.max_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.health_url) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            alive = {
                                m["machine_name"] for m in data["machines"]
                                if m["healthy"]
                            }
                            if all(name in alive for name in self.expected_machines):
                                return self.get_config_value("success", "pool_ready")
            except Exception:
                pass
            await asyncio.sleep(self.retry_interval)
        return self.get_config_value("timeout_event", "worker_crash")
```

### `run.sh`

```bash
#!/usr/bin/env bash
# Start: monitoring server, then supervisor (which spawns workers)
set -e
mkdir -p logs
python -m statemachine_engine.monitoring.websocket_server --port 3002 \
    > logs/monitor.log 2>&1 &
echo "Monitor PID: $!"
sleep 1
statemachine config/supervisor.yaml --machine-name supervisor \
    --debug > logs/supervisor.log 2>&1 &
echo "Supervisor PID: $!"
echo "UI: http://localhost:3002"
wait
```

### README outline

1. Architecture diagram (supervisor → workers, monitor server, browser)
2. What each state means and why
3. How the Kanban tab shows workers; how the Mermaid tab shows the supervisor
4. How to trigger drain: `statemachine-send-event drain supervisor`
5. How to verify health: `curl http://localhost:3002/machines/health`
6. How to add a 4th worker: change `pool_size`, add a `start_fsm` action

## Design decisions

**No `pool_size` as a runtime variable in this FR.** The example hard-codes
3 workers for clarity. Making `pool_size` dynamic (loop over `start_fsm` N
times) is a follow-on — the FSM engine does not yet have a `for` loop action.

**`health_check_action.py` as a custom action.** The `GET /machines/health`
call requires FR-FSM-017 to be shipped first. If FR-FSM-017 is not yet
available, the example can fall back to a `wait` + `wait_for_jobs` poll
approach. The README documents both variants.

**`template: false` for supervisor, `template: true` for workers.** One
Mermaid tab for the supervisor lifecycle (small, clear state diagram), Kanban
for the worker pool (N cards grouped by `worker_` prefix). This is the
canonical dual-template pattern from the NC-281 design.

**Crash handling simplified.** In this example, a "crash" is simulated by
`statemachine-send-event worker_crash supervisor`. Real crash detection (PID
monitoring, health polling) is out of scope — see `pid_check_action` as a
potential future action.

## Acceptance Criteria

- [ ] `examples/supervisor/` directory with all files above
- [ ] `run.sh` starts the monitoring server, then the supervisor (which auto-spawns 3 workers)
- [ ] After `run.sh`, `curl http://localhost:3002/machines/health` returns 200
      with 4 machines (`supervisor`, `worker_001`, `worker_002`, `worker_003`)
- [ ] Workers appear in Kanban grouped by `worker_` prefix (uses `_NNN` suffix → grouping regex)
- [ ] Supervisor appears in Mermaid tab (single machine, `template: false`)
- [ ] `statemachine-send-event drain supervisor` transitions supervisor → `draining` → `stopped`
- [ ] `README.md` covers architecture, run steps, drain walkthrough, and health check
- [ ] No new production code added to `statemachine_engine` package (pure example)
- [ ] Works with FR-FSM-017 shipped; degrades gracefully (documented fallback) without it

## Dependencies

| FR | Dependency type |
|----|----------------|
| FR-FSM-017 (machine health endpoint) | Soft — example uses it; fallback documented for when not shipped |
| FR-FSM-016 (event-driven completion) | None — example uses poll pattern; FR-016 would improve draining latency |

## Alternatives Considered

| Approach | Verdict |
|----------|---------|
| Extend `controller_worker` example with pool semantics | Rejected — conceptually distinct patterns; mixing them obscures both |
| Add `supervisor` as a first-class engine concept (builtin action `type: supervise_pool`) | Rejected — premature abstraction; one real use case (ninchat_voice) is not enough to generalise; implement as example first |
| Keep in `ninchat_voice` only | Rejected — the pattern is generic (no Twilio, no voice knowledge in the FSM YAML); ninchat_voice has it but can't share it |

## Related

- `examples/controller_worker/` — sibling example (job queue pattern)
- `examples/simple_worker/` — baseline single-worker example
- FR-FSM-016 — event-driven job completion (improves drain detection)
- FR-FSM-017 — machine health endpoint (used by `health_check_action.py`)
- `docs/parallel-state-machines.md` — background reading for multi-machine patterns
- `projects/ninchat_voice/docs/NC-280-supervisor-fork.md` — original voice supervisor design
- `projects/ninchat_voice/docs/NC-281-supervisor-monitoring.md` — monitoring layer (origin of this FR)
- `projects/ninchat_voice/feature-requests/NC-281-supervisor-monitoring.judgement.md` — judgement noting graduation path
