# Plan: Fix Concurrent Job Spawning

**Status**: ✅ **IMPLEMENTED** (2025-01-XX)  
**Implementation Summary**: See `concurrent-spawning-implementation.md`  
**Tests**: 27 passing (13 action tests + 14 database tests)

---

## Problem

Current `concurrent-controller.yaml` spawns jobs **sequentially**, not concurrently:

```
checking_queue (limit: 1) → spawn 1 job → wait for 1 job → loop back
```

This defeats the purpose of "concurrent" processing. We need:

```
checking_queue (get ALL) → spawn ALL jobs → wait for ALL jobs → loop back
```

## Current Flow Analysis

### States
- `checking_queue` - Gets 1 job at a time (limit: 1)
- `spawning_worker` - Spawns 1 worker
- `waiting_for_completion` - Waits for that 1 worker
- Loops back to get next job

### Issues
1. **Sequential Processing**: Only 1 job active at a time
2. **Inefficient**: Database polled after each job completes
3. **Not Concurrent**: Workers never run simultaneously

## Proposed Solution

### New State Machine Flow

```
                     ┌─────────────────┐
                     │ checking_queue  │
                     │ (get ALL jobs)  │
                     └────────┬────────┘
                              │ jobs_found
                     ┌────────▼────────┐
                ┌───→│ spawning_batch  │
                │    │ (spawn 1 job)   │
                │    └────────┬────────┘
                │             │ 
                │      worker_started
                │             │
                │    ┌────────▼─────────┐
                │    │ check_more_jobs  │
                │    │ (any pending?)   │
                │    └────────┬─────────┘
                │             │
                │    more_jobs│          no_more_jobs
                └─────────────┘                │
                                      ┌────────▼────────────┐
                                      │ waiting_for_batch   │
                                      │ (wait ALL complete) │
                                      └────────┬────────────┘
                                               │ all_complete
                                      ┌────────▼────────┐
                                      │ checking_queue  │
                                      └─────────────────┘
```

### State Definitions

1. **checking_queue**
   - Get ALL pending jobs from queue (remove `limit: 1`)
   - Store in context as `pending_jobs` list
   - If jobs found → `spawning_batch`
   - If no jobs → `idling`

2. **spawning_batch** (NEW)
   - Pop one job from `pending_jobs` list
   - Track job ID in `spawned_jobs`
   - Spawn worker FSM
   - → `check_more_jobs`

3. **check_more_jobs** (NEW)
   - Check if `pending_jobs` has more items
   - If yes → `spawning_batch` (spawn next)
   - If no → `waiting_for_batch` (all spawned)

4. **waiting_for_batch** (RENAMED from waiting_for_completion)
   - Use WaitForJobsAction to poll all spawned job IDs
   - Poll every 2 seconds via timeout(2)
   - When all complete → `checking_queue`

### Alternative Simpler Approach

Use a **loop within spawning_batch** instead of separate check state:

```yaml
spawning_batch:
  actions:
    - type: log
      message: "📦 Batch spawning: {pending_jobs|length} jobs remaining"
    
    - type: pop_from_list  # NEW ACTION NEEDED
      list_key: "pending_jobs"
      store_as: "current_job"
      success: has_job
      empty: batch_complete
    
    - type: add_to_list
      list_key: "spawned_jobs"
      value: "{current_job.id}"
    
    - type: start_fsm
      yaml_path: "examples/patient_records/config/patient-records.yaml"
      machine_name: "patient_record_{current_job.id}"
      ...
```

**Transitions:**
```yaml
- from: spawning_batch
  to: spawning_batch
  event: has_job      # Loop to spawn next

- from: spawning_batch
  to: waiting_for_batch
  event: batch_complete  # All spawned
```

## Implementation Plan

### Option 1: New PopFromListAction (Recommended)

**Pros:**
- Clean loop logic
- Single spawning state
- Reusable action for other use cases

**Cons:**
- Need to create new action

**Steps:**
1. Create `PopFromListAction`
   - Pop first item from list
   - Store in context key
   - Return different events for has_item vs empty

2. Modify `checking_queue`
   - Remove `limit: 1` from check_database_queue
   - Store results in `pending_jobs`

3. Rename `spawning_worker` → `spawning_batch`
   - Use `pop_from_list` to get next job
   - Loop back to self if more jobs
   - Transition to waiting when done

4. Rename `waiting_for_completion` → `waiting_for_batch`
   - No logic changes needed

### Option 2: Manual Counter (Alternative)

Use a counter and conditional logic:

```yaml
spawning_batch:
  actions:
    - type: set_context
      key: "current_index"
      value: "{current_index|default:0 + 1}"
    
    - type: set_context
      key: "current_job"
      value: "{jobs[current_index]}"
    
    # ... spawn logic ...
```

**Pros:**
- No new action needed

**Cons:**
- More complex YAML
- Harder to read
- Requires array indexing support

### Option 3: Separate States (Original Plan)

Keep `check_more_jobs` as separate state.

**Pros:**
- Explicit state for decision point
- Clear flow in diagram

**Cons:**
- Extra state transitions
- More complex FSM

## Recommended Approach

**Option 1** with PopFromListAction:

### File Changes

1. **Create `src/statemachine_engine/actions/builtin/pop_from_list_action.py`**
   ```python
   class PopFromListAction(BaseAction):
       """Pop first item from a list in context"""
       async def execute(self, context):
           list_key = self.config.get('list_key', 'items')
           store_as = self.config.get('store_as')
           
           items = context.get(list_key, [])
           if not items:
               return self.config.get('empty', 'list_empty')
           
           # Pop first item
           item = items.pop(0)
           context[list_key] = items  # Update list
           
           if store_as:
               context[store_as] = item
           
           return self.config.get('success', 'item_popped')
   ```

2. **Modify `concurrent-controller.yaml`**
   ```yaml
   states:
     - checking_queue
     - spawning_batch      # RENAMED
     - waiting_for_batch   # RENAMED
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
       event: worker_spawned   # Loop for next job
     
     - from: spawning_batch
       to: waiting_for_batch
       event: batch_complete   # All spawned
     
     - from: spawning_batch
       to: error_handling
       event: spawn_failed
     
     - from: waiting_for_batch
       to: checking_queue
       event: all_jobs_complete
     
     - from: waiting_for_batch
       to: waiting_for_batch
       event: timeout(2)
   
   actions:
     checking_queue:
       - type: log
         message: "🔍 Checking queue for ALL pending jobs..."
       
       - type: set_context
         key: "spawned_jobs"
         value: []
       
       - type: set_context
         key: "pending_jobs"
         value: []
       
       - type: check_database_queue
         status: pending
         # NO LIMIT - get all jobs
         machine_type: patient_records
         job_type: patient_records
         store_as: pending_jobs    # Store in pending_jobs
         success: jobs_found
         empty: no_jobs
     
     spawning_batch:
       - type: log
         message: "📦 Spawning batch: {pending_jobs|length} jobs remaining"
       
       - type: pop_from_list
         list_key: "pending_jobs"
         store_as: "current_job"
         success: has_job
         empty: batch_complete
       
       - type: add_to_list
         list_key: "spawned_jobs"
         value: "{current_job.id}"
       
       - type: start_fsm
         yaml_path: "examples/patient_records/config/patient-records.yaml"
         machine_name: "patient_record_{current_job.id}"
         context_vars:
           - current_job.id as job_id
           - report_id
           - report_title
           - summary_text
         success: worker_spawned
         error: spawn_failed
       
       - type: log
         message: "✅ Worker spawned: patient_record_{current_job.id}"
     
     waiting_for_batch:
       - type: log
         message: "⏳ Waiting for {spawned_jobs|length} workers to complete..."
       
       - type: wait_for_jobs
         tracked_jobs_key: "spawned_jobs"
         timeout: 300
         success: all_jobs_complete
         timeout_event: check_timeout
       
       - type: log
         message: "📊 Status - Completed: {completed_jobs|length}, Failed: {failed_jobs|length}, Pending: {pending_jobs|length}"
   ```

3. **Update `check_database_queue_action.py`**
   - Need to support returning ALL jobs (not just 1)
   - Add `store_as` parameter to put results in custom context key
   - Currently returns `jobs` - need to make this configurable

## Testing Plan

1. Create unit tests for PopFromListAction
2. Test with 5 jobs in queue
3. Verify all 5 workers spawn before any complete
4. Verify controller waits for all 5 to finish
5. Verify proper cleanup and next batch handling

## Expected Behavior After Fix

```
Cycle 1:
  checking_queue → Found 5 jobs
  spawning_batch → Spawn job_001 (4 remaining)
  spawning_batch → Spawn job_002 (3 remaining)
  spawning_batch → Spawn job_003 (2 remaining)
  spawning_batch → Spawn job_004 (1 remaining)
  spawning_batch → Spawn job_005 (0 remaining)
  waiting_for_batch → Waiting for 5 workers...
  [2 seconds pass]
  waiting_for_batch → 3 completed, 2 pending...
  [2 seconds pass]
  waiting_for_batch → 5 completed, 0 pending
  checking_queue → All complete, checking for more jobs

Cycle 2:
  checking_queue → Found 3 new jobs
  spawning_batch → Spawn job_006, job_007, job_008
  waiting_for_batch → Wait for 3 workers...
  ...
```

## Metrics

**Before:**
- 10 jobs = 10 sequential cycles = ~60 seconds (if each job takes 6s)

**After:**
- 10 jobs = 1 concurrent batch = ~6 seconds (all run in parallel)

**Improvement:** ~10x faster for batch processing
