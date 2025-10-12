# Change Request: check_database_queue Enhancement for v2.0 Architecture

## Summary

Request enhancement to `statemachine-engine`'s `check_database_queue` action to support **machine-agnostic queue checking**, enabling centralized controller architecture where one machine can poll and claim jobs regardless of `assigned_machine` field.

## Problem Statement

### Current Behavior

The builtin `check_database_queue_action.py` filters jobs by BOTH `job_type` AND `machine_type`:

```python
# statemachine_engine/actions/builtin/check_database_queue_action.py:42
job = self.job_model.get_next_job(job_type=self.job_type, machine_type=self.machine_type)
```

Which calls:

```python
# statemachine_engine/database/models/job.py:72-74
if machine_type:
    query += " AND machine_type = ?"
    params.append(machine_type)
```

**This prevents a controller from claiming jobs assigned to other machines.**

### V1.0 Architecture (Current)

- Jobs created with `assigned_machine` pre-set (e.g., `sdxl_generator`)
- Each worker polls for jobs WHERE `assigned_machine` matches their name
- **Works fine for distributed polling**

### V2.0 Architecture (Desired)

- **Controller** polls for jobs by `job_type` ONLY
- Controller claims ANY pending job of specified type
- Controller dispatches to workers via events (not database)
- Workers are purely event-driven (no DB polling)

**This is currently impossible** because `check_database_queue` requires `machine_type` match.

## Attempted Solutions

### Solution 1: Remove `machine_type` Parameter ❌

```yaml
# controller.yaml
checking_sdxl_queue:
  - type: check_database_queue
    job_type: sdxl_generation
    # No machine_type specified
```

**Result**: Action initializes with `self.machine_type = None` but:
- Job is still created with `assigned_machine='sdxl_generator'`
- `get_next_job(job_type='sdxl_generation', machine_type=None)` filters WHERE `machine_type IS NULL`
- No jobs found ❌

### Solution 2: Custom Controller Action ✅ (Current Workaround)

Created `controller/actions/check_queue_action.py`:

```python
async def execute(self, context: Dict[str, Any]) -> str:
    """Check queue without machine_type filter"""
    job = self.job_model.get_next_job(
        job_type=self.job_type,
        machine_type=None  # Explicitly bypass machine filter
    )
```

**Status**: ✅ **WORKING** - Controller test passes with this approach

## Requested Changes

### Option A: Update `get_next_job()` Behavior (Recommended)

Modify `job.py:get_next_job()` to treat `machine_type=None` as "match ANY machine":

```python
# statemachine_engine/database/models/job.py

def get_next_job(self, job_type: str = None, machine_type: str = None) -> Optional[Dict[str, Any]]:
    """Get next pending job with priority support and JSON parsing

    Args:
        job_type: Filter by job type (optional)
        machine_type: Filter by assigned machine (optional)
            - If None: match ANY machine (enables controller to claim any job)
            - If specified: match ONLY jobs assigned to that machine
    """
    with self.db._get_connection() as conn:
        query = "SELECT * FROM jobs WHERE status = 'pending'"
        params = []

        if job_type:
            query += " AND job_type = ?"
            params.append(job_type)

        # KEY CHANGE: Only filter by machine if explicitly provided
        if machine_type is not None:  # Changed from: if machine_type:
            query += " AND machine_type = ?"
            params.append(machine_type)

        query += " ORDER BY priority ASC, created_at ASC LIMIT 1"
        # ... rest unchanged
```

**Backward Compatibility**: ✅ Yes
- V1.0 workers continue passing `machine_type="worker_name"` → filtered query
- V2.0 controller passes `machine_type=None` → unfiltered query

### Option B: Add Explicit Flag (Alternative)

```python
def get_next_job(self, job_type: str = None, machine_type: str = None,
                 match_any_machine: bool = False) -> Optional[Dict[str, Any]]:
    """
    Args:
        match_any_machine: If True, ignore machine_type filter entirely
    """
    if machine_type and not match_any_machine:
        query += " AND machine_type = ?"
        params.append(machine_type)
```

**Usage**:
```python
# Controller
job = self.job_model.get_next_job(job_type='sdxl_generation', match_any_machine=True)

# Workers (V1.0)
job = self.job_model.get_next_job(job_type='face_processing', machine_type='face_processor')
```

## Testing Evidence

### Before Fix (Broken)

```
checking_sdxl_queue:
  - type: check_database_queue
    job_type: sdxl_generation

# Result:
[controller] waiting_idle --wake_up--> checking_sdxl_queue
[controller] (stuck - no new_sdxl_job event emitted)
```

### After Fix (Working)

```
checking_sdxl_queue:
  - type: check_queue  # Custom action
    job_type: sdxl_generation

# Result:
[controller] Claimed sdxl_generation job Controller_v2.0_Workflow_1760243488_sdxl
[controller] checking_sdxl_queue --new_sdxl_job--> dispatching_sdxl_job ✅
```

**Test Results**: ✅ `controller/tests/workflow/run-workflow-v2.sh` PASSED

```
✅ Queue polling: VERIFIED
✅ Job dispatch: VERIFIED
✅ Event-driven: VERIFIED
✅ Job lifecycle: VERIFIED
```

## Impact

**If Accepted**:
- ✅ Builtin `check_database_queue` supports both v1.0 (distributed) and v2.0 (centralized) architectures
- ✅ Custom `check_queue_action.py` no longer needed
- ✅ Cleaner, more maintainable solution

**If Rejected**:
- ⚠️ Projects using v2.0 architecture must maintain custom queue-checking actions
- ⚠️ Reduced portability between statemachine-engine projects

## References

**Code Locations**:
- `statemachine-engine/actions/builtin/check_database_queue_action.py:42`
- `statemachine-engine/database/models/job.py:62-114`

**Workaround Implementation**:
- `controller/actions/check_queue_action.py` (124 lines)

**Test Validation**:
- `controller/tests/workflow/run-workflow-v2.sh` (195 lines)

## Priority

**Medium** - Workaround exists, but enhances usability and eliminates need for custom per-project action duplication.

## Proposed By

v2.0 Architecture Refactoring (Centralized Controller Pattern)
Date: 2025-10-12

---

**Note**: This request is for `statemachine-engine` repository maintainers. The workaround (`check_queue_action.py`) is proven functional and can serve as reference implementation.
