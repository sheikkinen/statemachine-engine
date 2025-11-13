# Plan: Wait for Jobs Completion Action

**Date**: November 13, 2025  
**Context**: Current concurrent-controller spawns workers but doesn't wait for completion  
**Goal**: Add action to check all spawned jobs are completed before resuming polling

## Current Problem

The `concurrent-controller.yaml` spawns worker FSMs for each job but:
1. **Doesn't track spawned workers** - No record of which jobs were started
2. **Immediately returns to polling** - After spawning, it waits 5s then checks queue again
3. **Can spawn duplicates** - Same job might be spawned multiple times if not completed
4. **No completion verification** - Doesn't verify workers actually finished processing

### Current Flow
```
checking_queue → spawning_worker → waiting_for_completion (5s timeout) → checking_queue
                                             ↓
                                    (no actual verification!)
```

## Desired Behavior

Controller should:
1. **Track spawned jobs** - Remember which job IDs were started
2. **Wait for completion** - Poll database until all spawned jobs are completed/failed
3. **Resume polling** - Only check for new jobs after current batch finishes
4. **Handle failures** - Detect and handle failed jobs appropriately

### Desired Flow
```
checking_queue → spawning_worker → waiting_for_completion → all_jobs_complete → checking_queue
                       ↓                      ↓                      ↓
                  track job_id        check database        verify ALL tracked
                                      for status             jobs are done
```

## Solution Design

### New Action: `WaitForJobsAction`

**Purpose**: Check database to verify all tracked jobs have reached terminal states (completed/failed)

**Location**: `src/statemachine_engine/actions/builtin/wait_for_jobs_action.py`

**Configuration**:
```yaml
actions:
  waiting_for_completion:
    - type: wait_for_jobs
      tracked_jobs_key: "spawned_jobs"  # Context key with list of job IDs
      poll_interval: 2                   # Seconds between checks (default: 2)
      timeout: 300                       # Max wait time in seconds (default: 300)
      success: all_jobs_complete         # All jobs done
      timeout_event: check_timeout       # Timeout reached, jobs still pending
```

**Return Events**:
- `all_jobs_complete` - All tracked jobs are completed or failed
- `check_timeout` - Timeout reached, some jobs still processing
- `no_jobs_tracked` - No jobs to wait for (empty list)

**Context Requirements**:
- Reads: `context[tracked_jobs_key]` - List of job IDs to track
- Writes: `context['completed_jobs']` - List of completed job IDs
- Writes: `context['failed_jobs']` - List of failed job IDs
- Writes: `context['pending_jobs']` - List of still-processing job IDs

### Database Query

Query jobs table for all tracked job IDs:
```sql
SELECT job_id, status, completed_at, started_at
FROM jobs
WHERE job_id IN (?, ?, ...)
```

Terminal states:
- `completed` - Job finished successfully
- `failed` - Job failed with error

Non-terminal states:
- `pending` - Not started yet (shouldn't happen if we track spawned jobs)
- `processing` - Still running

### Implementation Steps

#### Phase 1: Create WaitForJobsAction

1. **Create action file**:
   ```python
   class WaitForJobsAction(BaseAction):
       def __init__(self, config):
           self.tracked_jobs_key = config.get('tracked_jobs_key', 'spawned_jobs')
           self.poll_interval = config.get('poll_interval', 2)
           self.timeout = config.get('timeout', 300)
       
       async def execute(self, context):
           # Get tracked job IDs from context
           job_ids = context.get(self.tracked_jobs_key, [])
           
           if not job_ids:
               return 'no_jobs_tracked'
           
           # Query database for job statuses
           statuses = self._get_job_statuses(job_ids)
           
           # Categorize jobs
           completed = [j for j, s in statuses.items() if s == 'completed']
           failed = [j for j, s in statuses.items() if s == 'failed']
           pending = [j for j, s in statuses.items() if s in ('pending', 'processing')]
           
           # Store in context
           context['completed_jobs'] = completed
           context['failed_jobs'] = failed
           context['pending_jobs'] = pending
           
           # Check if all done
           if not pending:
               return 'all_jobs_complete'
           
           # Still have pending jobs
           return 'jobs_pending'
   ```

2. **Add database query method**:
   ```python
   def _get_job_statuses(self, job_ids):
       """Query database for status of all tracked jobs"""
       with self.job_model.db._get_connection() as conn:
           placeholders = ','.join(['?'] * len(job_ids))
           query = f"""
               SELECT job_id, status
               FROM jobs
               WHERE job_id IN ({placeholders})
           """
           rows = conn.execute(query, job_ids).fetchall()
           return {row['job_id']: row['status'] for row in rows}
   ```

3. **Add tests**:
   - `test_wait_for_jobs_all_complete` - All jobs completed
   - `test_wait_for_jobs_some_failed` - Mix of completed/failed
   - `test_wait_for_jobs_still_pending` - Some still processing
   - `test_wait_for_jobs_no_jobs_tracked` - Empty list
   - `test_wait_for_jobs_timeout` - Timeout behavior

#### Phase 2: Update concurrent-controller.yaml

1. **Add job tracking in spawning_worker**:
   ```yaml
   spawning_worker:
     - type: log
       message: "🚀 Spawning worker for job: {current_job.id}"
       level: info
     
     # Track this job ID before spawning
     - type: bash
       command: "echo 'Tracking job {current_job.id}'"
       success: tracked
     
     - type: start_fsm
       yaml_path: "examples/patient_records/config/patient-records.yaml"
       machine_name: "patient_record_{current_job.id}"
       context_vars:
         - current_job.id as job_id
         - report_id
         - report_title
         - summary_text
       success: worker_started
       error: spawn_failed
       store_pid: true
   ```

2. **Add job ID to context tracking**:
   ```yaml
   # Need custom action or bash trick to build list
   # Option A: Use bash to append to file, read file to get list
   # Option B: Create custom action to manage list in context
   # Option C: Store in database as metadata
   ```

3. **Update waiting_for_completion state**:
   ```yaml
   waiting_for_completion:
     - type: log
       message: "⏳ Waiting for spawned jobs to complete..."
       level: info
     
     - type: wait_for_jobs
       tracked_jobs_key: "spawned_jobs"
       poll_interval: 2
       timeout: 300
       success: all_jobs_complete
       pending: still_waiting
       timeout_event: check_timeout
   ```

4. **Add new transitions**:
   ```yaml
   transitions:
     # Wait for jobs to complete
     - from: waiting_for_completion
       to: checking_queue
       event: all_jobs_complete
     
     # Keep waiting if jobs still pending
     - from: waiting_for_completion
       to: waiting_for_completion
       event: still_waiting
     
     # Timeout handling
     - from: waiting_for_completion
       to: error_handling
       event: check_timeout
   ```

#### Phase 3: Job Tracking Strategy

**Challenge**: Need to track list of spawned job IDs across multiple spawns

**Options**:

1. **Context List Management** (Recommended):
   - Create helper action: `AddToListAction`
   - Maintains list in context: `context['spawned_jobs'].append(job_id)`
   - Simple, in-memory, cleared when controller restarts

2. **Database Metadata**:
   - Store spawned job IDs in controller's metadata
   - Persist across restarts
   - More complex to implement

3. **File-based Tracking**:
   - Write job IDs to file: `data/spawned_jobs.txt`
   - Read file in wait action
   - Simple but fragile

**Chosen Approach**: Context List Management

Create `AddToListAction`:
```python
class AddToListAction(BaseAction):
    """Add item to a list in context"""
    
    async def execute(self, context):
        list_key = self.config.get('list_key', 'items')
        value = self.config.get('value')  # Supports interpolation
        
        if list_key not in context:
            context[list_key] = []
        
        context[list_key].append(value)
        
        return 'success'
```

Usage:
```yaml
spawning_worker:
  - type: add_to_list
    list_key: "spawned_jobs"
    value: "{current_job.id}"
    success: tracked
  
  - type: start_fsm
    # ... spawn worker
```

#### Phase 4: Enhanced Logging

Add activity logging to track workflow:

```yaml
spawning_worker:
  - type: activity_log
    message: "Spawning worker for job {current_job.id}"
    level: info
  
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
    success: worker_started
  
  - type: activity_log
    message: "Worker spawned successfully"
    level: success

waiting_for_completion:
  - type: activity_log
    message: "Waiting for {spawned_jobs|length} jobs to complete"
    level: info
  
  - type: wait_for_jobs
    tracked_jobs_key: "spawned_jobs"
    success: all_jobs_complete
    pending: still_waiting
  
  - type: activity_log
    message: "Jobs status - Completed: {completed_jobs|length}, Failed: {failed_jobs|length}, Pending: {pending_jobs|length}"
    level: info
```

## Implementation Timeline

### Estimated Effort: 2-3 hours

1. **Phase 1 - WaitForJobsAction** (1 hour)
   - Create action class
   - Add database query
   - Write tests (5-6 test cases)

2. **Phase 2 - AddToListAction** (30 min)
   - Create helper action
   - Add tests
   - Update builtin __init__.py

3. **Phase 3 - Update concurrent-controller** (30 min)
   - Add job tracking
   - Update transitions
   - Add new states if needed
   - Enhanced logging

4. **Phase 4 - Integration Testing** (1 hour)
   - Test with patient_records demo
   - Verify job tracking works
   - Test timeout scenarios
   - Verify no duplicate spawns

## Testing Plan

### Unit Tests

1. **WaitForJobsAction**:
   - All jobs completed successfully
   - Mix of completed and failed jobs
   - Some jobs still pending
   - Empty job list
   - Invalid job IDs
   - Timeout behavior

2. **AddToListAction**:
   - Create new list
   - Append to existing list
   - Variable interpolation in value
   - Multiple appends

### Integration Tests

1. **Concurrent Controller Flow**:
   - Spawn single worker, wait for completion
   - Spawn multiple workers, wait for all
   - Handle failed jobs gracefully
   - Resume polling after completion
   - No duplicate job spawns

2. **Patient Records Demo**:
   - Create 5 jobs in database
   - Start controller
   - Verify all 5 workers spawn
   - Verify controller waits
   - Verify controller resumes after all complete

## Success Criteria

✅ Controller tracks spawned job IDs  
✅ Controller waits for all tracked jobs to complete  
✅ Controller resumes polling only after batch completes  
✅ Failed jobs are detected and logged  
✅ No duplicate job spawns  
✅ Timeout handling works correctly  
✅ Activity logging shows clear workflow progression  
✅ All tests pass  

## Future Enhancements

1. **Batch Size Limit**: Spawn max N jobs, wait, then spawn next batch
2. **Parallel Polling**: Check multiple jobs in parallel for faster detection
3. **Event-based Completion**: Workers send event to controller when done
4. **Retry Logic**: Automatically retry failed jobs
5. **Job Priority**: Process high-priority jobs first

## Notes

- This is a synchronous wait pattern (polling database)
- Alternative: Event-driven pattern where workers send `job_complete` event
- Current approach simpler, no cross-machine event handling needed
- Polling every 2s is acceptable for demo/prototype
- Production systems should use event-driven approach

## Related Actions

- `check_database_queue` - Polls for new jobs (existing)
- `start_fsm` - Spawns worker machines (existing)
- `complete_job` - Marks job as complete (existing)
- `wait_for_jobs` - NEW - Waits for tracked jobs
- `add_to_list` - NEW - Helper for job tracking
