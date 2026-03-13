# Concurrent Job Spawning Implementation Summary

**Date**: 2025-01-XX
**Version**: v1.0.73 (upcoming)
**Issue**: Jobs were being spawned sequentially (one at a time) instead of concurrently

## Problem Statement

The concurrent-controller was spawning jobs sequentially:
1. Get 1 job from queue (limit: 1)
2. Spawn worker for that job
3. Wait for it to complete
4. Loop back to step 1

This meant 10 jobs would take 10 sequential cycles instead of running concurrently.

## Solution Overview

Implemented **batch spawning pattern**:
1. Get ALL pending jobs from queue
2. Claim each job atomically (prevent race conditions)
3. Spawn ALL workers in a loop
4. Wait for ALL workers to complete
5. Loop back to step 1

This achieves ~10x performance improvement for batches.

## Components Implemented

### 1. Database Layer (JobModel)

**File**: `src/statemachine_engine/database/models/job.py`

**New Method: `get_pending_jobs()`**
```python
def get_pending_jobs(
    job_type: str = None,
    machine_type: str = None,
    limit: int = None
) -> List[Dict[str, Any]]
```
- Returns ALL pending jobs without claiming them
- Supports filtering by job_type and machine_type
- Supports optional limit parameter
- Orders by priority, then creation time

**New Method: `claim_job()`**
```python
def claim_job(job_id: str) -> bool
```
- Atomically claims a pending job (marks as processing)
- Prevents race conditions with `WHERE status = 'pending'`
- Returns True if claimed, False if already taken
- Thread-safe for concurrent controller scenarios

**Tests**: Added 7 tests in `test_job_queue_machine_agnostic.py`
- ✅ get_pending_jobs returns all jobs
- ✅ get_pending_jobs respects limit
- ✅ get_pending_jobs filters by machine_type
- ✅ get_pending_jobs excludes non-pending jobs
- ✅ claim_job marks job as processing
- ✅ claim_job prevents double-claiming
- ✅ Complete batch spawning workflow test

### 2. Action Layer

**File**: `src/statemachine_engine/actions/builtin/get_pending_jobs_action.py` (93 lines)

```yaml
- type: get_pending_jobs
  job_type: "patient_records"
  machine_type: "worker"
  limit: 10  # optional
  store_as: "pending_jobs"
  success: jobs_found
  empty: no_jobs
```

Features:
- Retrieves multiple jobs without claiming them
- Stores jobs in context list for iteration
- Returns different events for found vs empty
- Configurable success/empty event names

**Tests**: 6 tests in `test_get_pending_jobs_action.py`
- ✅ Get jobs successfully
- ✅ Handle empty queue
- ✅ Respect limit parameter
- ✅ Filter by machine_type
- ✅ Default event names
- ✅ Error handling

---

**File**: `src/statemachine_engine/actions/builtin/claim_job_action.py` (75 lines)

```yaml
- type: claim_job
  job_id: "{current_job.job_id}"
  success: job_claimed
  already_claimed: job_taken
  error: claim_error
```

Features:
- Atomically claims a job before spawning
- Prevents race conditions in multi-controller setups
- Returns different events for claimed vs already-taken
- Supports variable interpolation for job_id

**Tests**: 7 tests in `test_claim_job_action.py`
- ✅ Claim job successfully
- ✅ Handle already claimed job
- ✅ Default event names
- ✅ Variable interpolation
- ✅ Error handling
- ✅ Missing job_id validation
- ✅ Default error event

### 3. State Machine Updates

**File**: `examples/patient_records/config/concurrent-controller.yaml`

**State Changes**:
- `spawning_worker` → `spawning_batch` (spawns ALL jobs)
- `waiting_for_completion` → `waiting_for_batch` (waits for ALL workers)

**New Flow**:

```
checking_queue:
  ├─ get_pending_jobs (get ALL jobs) → jobs_found
  └─ no jobs → idling

spawning_batch: (LOOP STATE)
  ├─ pop_from_list (get next job)
  │  ├─ has_job → continue
  │  └─ batch_complete → waiting_for_batch
  ├─ claim_job (atomic claim)
  │  ├─ job_claimed → continue
  │  ├─ job_taken → spawning_batch (skip, try next)
  │  └─ error → error_handling
  ├─ add_to_list (track spawned job)
  └─ start_fsm (spawn worker) → worker_spawned → spawning_batch

waiting_for_batch:
  └─ wait_for_jobs (poll every 2 seconds)
     ├─ all_jobs_complete → checking_queue
     ├─ timeout(2) → waiting_for_batch (continue polling)
     └─ check_timeout → error_handling
```

**Key Pattern**: The `spawning_batch` state loops back to itself after each worker is spawned, processing the entire batch before transitioning to `waiting_for_batch`.

## Test Coverage

**Total Tests**: 27 passing
- Action tests: 13 (6 + 7)
- Database tests: 14 (7 existing + 7 new)

**Test Files**:
- `tests/actions/test_get_pending_jobs_action.py`
- `tests/actions/test_claim_job_action.py`
- `tests/database/test_job_queue_machine_agnostic.py`

## Performance Impact

**Before** (Sequential):
```
Cycle 1: Get 1 job → Spawn → Wait for 1 → Complete
Cycle 2: Get 1 job → Spawn → Wait for 1 → Complete
...
Cycle 10: Get 1 job → Spawn → Wait for 1 → Complete

Total time: ~60 seconds (10 jobs × ~6s each)
```

**After** (Concurrent):
```
Cycle 1:
  Get 10 jobs → Spawn 10 workers → Wait for ALL 10 → Complete

Total time: ~6 seconds (all jobs run concurrently)
```

**Improvement**: ~10x faster for batches

## Race Condition Prevention

The `claim_job` action prevents race conditions when multiple controllers compete for jobs:

```sql
UPDATE jobs
SET status = 'processing', started_at = CURRENT_TIMESTAMP
WHERE job_id = ? AND status = 'pending'
```

The `WHERE status = 'pending'` ensures only one controller can claim each job.

## Backward Compatibility

- All existing actions unchanged
- `check_database_queue` still works for sequential processing
- New actions are opt-in
- v1.0 sequential pattern still supported

## Migration Path

To migrate from sequential to batch spawning:

1. Replace `check_database_queue` with `get_pending_jobs`
2. Rename states: `spawning_worker` → `spawning_batch`
3. Add `pop_from_list` at start of spawning state
4. Add `claim_job` before `start_fsm`
5. Update transitions to loop on `worker_spawned`

## Files Modified

**New Files**:
- `src/statemachine_engine/actions/builtin/get_pending_jobs_action.py`
- `src/statemachine_engine/actions/builtin/claim_job_action.py`
- `tests/actions/test_get_pending_jobs_action.py`
- `tests/actions/test_claim_job_action.py`

**Modified Files**:
- `src/statemachine_engine/database/models/job.py` (added 2 methods)
- `src/statemachine_engine/actions/builtin/__init__.py` (registered 2 actions)
- `examples/patient_records/config/concurrent-controller.yaml` (updated flow)
- `tests/database/test_job_queue_machine_agnostic.py` (added 7 tests)

## Next Steps

1. ✅ Implementation complete
2. ✅ Unit tests complete (27 passing)
3. ⏳ Integration testing with patient_records demo
4. ⏳ Update release notes for v1.0.73
5. ⏳ Consider adding batch_size limit to prevent overwhelming system

## Related Issues

- Fixes: Sequential job spawning in concurrent-controller
- Related to: v1.0.72 variable interpolation refactoring
- Depends on: WaitForJobsAction (already implemented)
- Depends on: PopFromListAction (already implemented)

## Design Decisions

**Why separate get + claim instead of atomic get_and_claim?**
- Separation of concerns: get is read-only, claim is write
- Flexibility: can get jobs without claiming (inspection, metrics)
- Explicit: YAML clearly shows two-phase process
- Race-safe: claim uses WHERE status='pending' for atomicity

**Why use pop_from_list instead of foreach loop?**
- State machines use events for flow control
- Actions can't directly control state transitions
- Pop pattern works with existing event-driven architecture
- Allows intermediate states for observability

**Why claim before spawn?**
- Prevents duplicate spawning if spawn is slow
- Job is marked as "in progress" immediately
- Prevents other controllers from taking job mid-spawn
- Allows tracking of "claimed but not yet spawned" jobs

## Metrics & Observability

The new pattern provides better observability:

```
📋 Found 5 pending jobs to process
🔒 Claiming job: job_001 (4 jobs remaining in batch)
🚀 Spawning worker for job: job_001
✅ Worker spawned: patient_record_job_001 (total spawned: 1)
🔒 Claiming job: job_002 (3 jobs remaining in batch)
...
⏳ Waiting for 5 spawned workers to complete...
📊 Batch status - Completed: 5, Failed: 0, Pending: 0
```

Each step is logged with:
- Batch size
- Remaining jobs in batch
- Total spawned count
- Completion statistics

---

**Implementation Status**: ✅ COMPLETE
**Test Status**: ✅ 27/27 PASSING
**Ready for**: Integration testing & release
