# Parallel State Machines

How to spawn and manage multiple concurrent FSM instances using the controller/worker pattern.

---

## Overview

The engine supports true process-level parallelism: a **controller FSM** reads a job queue, spawns **worker FSMs** as independent OS processes, tracks them via the database, and waits for the batch to finish before polling again.

```
Controller FSM                         Worker FSMs (OS processes)
─────────────────────────────────      ──────────────────────────────
checking_queue                         patient_record_001  ─── summarizing
      │ jobs_found                     patient_record_002  ─── fact_checking
      ▼                                patient_record_003  ─── ready
spawning_batch ──loop──▶ (per job)     patient_record_004  ─── summarizing
      │ batch_complete                 ...
      ▼
waiting_for_batch ──poll──▶ (2s)
      │ all_jobs_complete
      ▼
checking_queue
```

---

## YAML Configuration

### Worker FSM (`worker.yaml`)

Mark the worker as `template: true` — this tells the UI to show Kanban view instead of a unique diagram.

```yaml
name: "patient-records"
initial_state: summarizing
template: true          # ← renders as Kanban in the UI

states:
  - summarizing
  - fact_checking
  - ready
  - failed
  - shutdown

transitions:
  - from: summarizing
    to: fact_checking
    event: timeout(30)
  - from: fact_checking
    to: ready
    event: timeout(30)
  - from: "*"
    to: shutdown
    event: stop

actions:
  ready:
    - type: complete_job      # ← marks job done in DB so controller can proceed
      job_id: "{job_id}"
      success: job_completed
    - type: bash
      command: "echo done"
      success: stop
```

### Controller FSM (`controller.yaml`)

Mark the controller as `template: false` — it is unique and shown as a Mermaid diagram.

```yaml
name: "concurrent-controller"
initial_state: checking_queue
template: false

states:
  - checking_queue
  - spawning_batch
  - waiting_for_batch
  - idling
  - error_handling

transitions:
  - from: checking_queue
    to: spawning_batch
    event: jobs_found
  - from: checking_queue
    to: idling
    event: no_jobs

  - from: spawning_batch
    to: spawning_batch
    event: worker_spawned     # loop: next job
  - from: spawning_batch
    to: spawning_batch
    event: job_taken          # race condition: another controller claimed this job
  - from: spawning_batch
    to: waiting_for_batch
    event: batch_complete     # all jobs in list have been spawned
  - from: spawning_batch
    to: error_handling
    event: spawn_failed

  - from: waiting_for_batch
    to: checking_queue
    event: all_jobs_complete
  - from: waiting_for_batch
    to: waiting_for_batch
    event: timeout(2)         # poll every 2 seconds
  - from: waiting_for_batch
    to: error_handling
    event: check_timeout

  - from: idling
    to: checking_queue
    event: timeout(10)

  - from: error_handling
    to: checking_queue
    event: retry

actions:
  checking_queue:
    # Reset tracking list for the new batch
    - type: set_context
      key: "spawned_jobs"
      value: []

    # Fetch all pending jobs without claiming them
    - type: get_pending_jobs
      job_type: patient_records
      store_as: "pending_jobs"
      success: jobs_found
      empty: no_jobs

  spawning_batch:
    # Pop next job off the list (returns batch_complete when empty)
    - type: pop_from_list
      list_key: "pending_jobs"
      store_as: "current_job"
      success: has_job
      empty: batch_complete

    # Atomically claim the job to prevent duplicate spawning
    - type: claim_job
      job_id: "{current_job.job_id}"
      success: job_claimed
      already_claimed: job_taken
      error: spawn_failed

    # Track this job so we can wait for it later
    - type: add_to_list
      list_key: "spawned_jobs"
      value: "{current_job.job_id}"

    # Spawn the worker as an independent OS process
    - type: start_fsm
      yaml_path: "config/patient-records.yaml"
      machine_name: "patient_record_{current_job.job_id}"
      context_vars:
        - current_job.job_id as job_id
        - current_job.data.report_id as report_id
        - current_job.data.report_title as report_title
      success: worker_spawned
      error: spawn_failed

  waiting_for_batch:
    # Poll DB until all tracked jobs reach completed/failed
    - type: wait_for_jobs
      tracked_jobs_key: "spawned_jobs"
      poll_interval: 2
      timeout: 300
      success: all_jobs_complete
      timeout_event: check_timeout

  idling:
    - type: log
      message: "Queue empty — sleeping 10s"
      level: info

  error_handling:
    - type: log
      message: "Batch error — retrying"
      level: error
    - type: bash
      command: "echo retrying"
      success: retry
```

---

## Built-in Actions for Parallel Patterns

### `get_pending_jobs` — fetch the whole queue

Reads all pending jobs **without claiming** them. Stores a list in context.

```yaml
- type: get_pending_jobs
  job_type: "patient_records"   # optional filter
  machine_type: "worker"        # optional filter
  limit: 20                     # optional cap
  store_as: "pending_jobs"      # context key (default: pending_jobs)
  success: jobs_found
  empty: no_jobs
```

Context after: `context["pending_jobs"]` = list of job dicts with `.job_id`, `.data.*`.

---

### `pop_from_list` — iterate the batch

Removes and returns the first item from a context list. Loop the state back to itself to process every item.

```yaml
- type: pop_from_list
  list_key: "pending_jobs"
  store_as: "current_job"
  success: has_job        # item popped
  empty: batch_complete   # list exhausted
```

---

### `claim_job` — atomic ownership

Marks a job `processing` with a `WHERE status = 'pending'` guard. Prevents two controllers from spawning the same job.

```yaml
- type: claim_job
  job_id: "{current_job.job_id}"
  success: job_claimed
  already_claimed: job_taken   # another controller got it first
  error: spawn_failed
```

---

### `add_to_list` — track spawned IDs

Appends a value to a context list, creating it if absent.

```yaml
- type: add_to_list
  list_key: "spawned_jobs"
  value: "{current_job.job_id}"
```

---

### `start_fsm` — spawn a worker process

Launches `statemachine <yaml_path> --machine-name <name>` as a detached OS process (`start_new_session=True`). Returns immediately — the worker runs independently.

```yaml
- type: start_fsm
  yaml_path: "config/worker.yaml"
  machine_name: "worker_{job_type}_{job_id}"  # supports {variable} interpolation
  context_vars:                               # what to pass to the child process
    - current_job.job_id as job_id            # nested path → renamed key
    - current_job.data.report_id as report_id
    - report_title                            # flat copy
  success: worker_spawned
  error: spawn_failed
  store_pid: true                             # optional: append PID to context["spawned_pids"]
```

**`context_vars` syntax:**
| Form | Meaning |
|------|---------|
| `variable_name` | copy `context["variable_name"]` as-is |
| `parent.child.field` | extract nested value using dot notation |
| `source as target` | extract and rename in the child context |

Values are serialised to JSON and passed via `--initial-context` on the CLI.

---

### `wait_for_jobs` — block until batch is done

Polls the database and returns when every tracked job ID reaches `completed` or `failed`.

```yaml
- type: wait_for_jobs
  tracked_jobs_key: "spawned_jobs"   # context key holding list of job IDs
  poll_interval: 2                   # seconds between checks (default: 2)
  timeout: 300                       # max wait seconds (default: 300)
  success: all_jobs_complete         # all done
  timeout_event: check_timeout       # timeout reached, some still pending
```

Context written by this action:
- `completed_jobs` — IDs that reached `completed`
- `failed_jobs` — IDs that reached `failed`
- `pending_jobs` — IDs still processing

---

### `complete_job` — signal completion from worker

Call this in the worker's terminal state. Updates the job row to `completed` so the controller's `wait_for_jobs` poll can unblock.

```yaml
- type: complete_job
  job_id: "{job_id}"
  success: job_completed
  error: completion_failed
```

---

## Running the Example

```bash
# From the fsm/ repo root

# 1. Seed the database with jobs
statemachine-db add-job --job-type patient_records --data '{"report_id":"R001","report_title":"Annual Physical"}'
statemachine-db add-job --job-type patient_records --data '{"report_id":"R002","report_title":"Blood Test"}'

# 2. Start the UI (optional — open http://localhost:3001)
statemachine-ui

# 3. Start the controller (it will spawn workers automatically)
statemachine examples/patient_records/config/concurrent-controller.yaml \
    --machine-name concurrent-controller

# 4. Or run the full demo script
./examples/patient_records/run-demo.sh start
```

In the UI, click the **Patient Records** tab → the Kanban board shows every worker as a card moving through `summarizing → fact_checking → ready`.

---

## UI: Kanban vs Diagram

| YAML field | Value | UI behaviour |
|-----------|-------|--------------|
| `template: true` | worker | Kanban board — all instances as cards in state columns |
| `template: false` | controller | Mermaid state diagram — single unique machine |

Tab grouping: machines named `<base>_NNN` (e.g. `patient_record_001`) are grouped under one tab with an instance count badge.

---

## Running Multiple Independent Controller/Worker Clusters

Each cluster needs its own socket paths to avoid interference:

```bash
# Cluster A
statemachine controller-a.yaml \
    --event-socket-path /tmp/cluster-a.sock \
    --control-socket-prefix /tmp/cluster-a-control

# Cluster B
statemachine controller-b.yaml \
    --event-socket-path /tmp/cluster-b.sock \
    --control-socket-prefix /tmp/cluster-b-control

# Monitor Cluster A
python -m statemachine_engine.monitoring.websocket_server \
    --port 3002 --event-socket-path /tmp/cluster-a.sock

# Monitor Cluster B
python -m statemachine_engine.monitoring.websocket_server \
    --port 3003 --event-socket-path /tmp/cluster-b.sock
```

See `docs/multiple-engines.md` for full details.

---

## Key Design Decisions

**Why OS processes and not threads/asyncio tasks?**  
Each FSM instance has its own YAML config, event loop, and log file. Process isolation means a crashed worker cannot corrupt the controller or other workers.

**Why poll the database instead of sending events?**  
The worker and controller are independent processes with no shared memory. The database is the natural rendezvous point. Event-driven completion is a future enhancement.

**Why claim before spawn?**  
`get_pending_jobs` reads without locking. If two controllers run simultaneously, both see the same pending list. `claim_job` uses an atomic `UPDATE WHERE status = 'pending'` so only one wins — the other gets `already_claimed` and moves to the next job.
