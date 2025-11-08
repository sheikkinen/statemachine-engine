# Status: Context Passing Implementation

**Date:** November 8, 2025  
**Feature:** Context Passing from Controller to Spawned Workers  
**Status:** ✅ Complete and Deployed

## Executive Summary

Successfully implemented and deployed context passing mechanism that enables controller FSMs to pass job-specific data to dynamically spawned worker FSMs. This resolves the issue where workers were stuck in idle state waiting for events that never arrived.

**Key Achievement:** Workers now auto-start with job context and begin processing immediately upon spawn.

## Problem Statement

### Original Issue
Workers were stuck in idle state after being spawned by the controller:
- Workers remained in `waiting_for_report` state indefinitely
- Controller spawned workers but never sent `new_report` event
- Workers lacked job context (job_id, report_id, etc.) needed for processing
- Jobs remained in "processing" status in database but never completed

### Root Cause
1. Controller spawned workers but had no mechanism to pass job-specific data
2. Workers started in `waiting_for_report` state expecting an event trigger
3. No event was sent, creating a deadlock situation
4. Even if event was sent, workers wouldn't have job context

## Solution Design

### Architecture Decision
Implemented CLI-based context passing using `--initial-context` JSON argument:

**Approach:**
```bash
statemachine worker.yaml --machine-name worker_001 \
  --initial-context '{"job_id":"job_001","report_id":"report_1"}'
```

**Advantages:**
- Visible in process list (debuggable with `ps aux`)
- No shared state between processes
- Simple to implement and test
- Works with existing subprocess spawning

**Rejected Alternatives:**
- Environment variables (harder to debug, size limits)
- Unix socket message after spawn (complex, race conditions)

### Component Changes

#### 1. StartFsmAction Enhancement
**File:** `src/statemachine_engine/actions/builtin/start_fsm_action.py`

**New Features:**
- `context_vars` parameter in YAML config
- `_extract_context_vars()` method for variable extraction
- `_get_nested_value()` method for dot notation support

**Syntax Support:**
```yaml
context_vars:
  - simple_var              # Flat variable
  - parent.child.field      # Nested (dot notation)
  - source as target        # Renamed variable
```

**Implementation:**
- Extracts specified variables from parent context
- Serializes to JSON and adds `--initial-context` argument
- Warns if context exceeds 4KB
- Gracefully handles missing variables (logs warning, continues)

#### 2. CLI Enhancement
**File:** `src/statemachine_engine/cli.py`

**New Features:**
- `--initial-context` command-line argument
- JSON parsing with error handling
- Context merging with job_model data

**Implementation:**
```python
parser.add_argument('--initial-context', type=str, default='{}',
                   help='JSON string with initial context variables')

# Parse and merge
user_context = json.loads(initial_context_json)
initial_context.update(user_context)
```

#### 3. Worker FSM Refactoring
**File:** `examples/patient_records/config/patient-records.yaml`

**Changes:**
- **Before:** `initial_state: waiting_for_report`
- **After:** `initial_state: summarizing`

**Removed:**
- `waiting_for_report` state
- `new_report` event
- Event-based triggering logic

**Added:**
- Context verification logging:
  ```
  🔍 Context verification - Job ID: {job_id}, Report: {report_id} ({report_title})
  ```

**Impact:** Workers auto-start in processing state upon spawn

#### 4. Controller Configuration
**File:** `examples/patient_records/config/concurrent-controller.yaml`

**Added:**
```yaml
- type: start_fsm
  config:
    config_file: examples/patient_records/config/patient-records.yaml
    machine_name: 'patient_record_{current_job.id}'
    context_vars:
      - current_job.id as job_id
      - report_id
      - report_title
      - summary_text
```

**Context Variables Passed:**
- `current_job.id` → renamed to `job_id`
- `report_id` (from job_data)
- `report_title` (from job_data)
- `summary_text` (from job_data)

## Test Coverage

### TDD Approach
Followed Test-Driven Development:
1. **RED Phase:** Wrote 7 failing tests
2. **GREEN Phase:** Implemented features to pass tests
3. **REFACTOR:** Updated documentation

### New Tests (7)
**File:** `tests/actions/test_start_fsm_action.py`

1. `test_start_fsm_with_context_vars` - Basic variable extraction
2. `test_start_fsm_with_nested_context_vars` - Dot notation support
3. `test_start_fsm_with_renamed_context_vars` - "as" syntax
4. `test_start_fsm_missing_context_vars` - Graceful error handling
5. `test_start_fsm_empty_context_vars` - No arg when not specified
6. `test_start_fsm_empty_context_vars_list` - Empty list handling
7. `test_start_fsm_large_context_warning` - Size warning for >4KB

### Test Results
- **StartFsmAction:** 18/18 tests passing ✅
- **Full Suite:** 232/241 tests passing (9 skipped) ✅
- **No Regressions:** All 11 original tests still pass ✅

## Integration Verification

### Manual Integration Test
**Command:**
```bash
statemachine examples/patient_records/config/patient-records.yaml \
  --machine-name test_worker \
  --initial-context '{"job_id":"job_TEST","report_id":"report_test","report_title":"Test Report"}'
```

**Output (Verified):**
```
INFO - Initial context provided: ['job_id', 'report_id', 'report_title']
INFO - Action log: 🔍 Context verification - Job ID: job_TEST, Report: report_test (Test Report)
INFO - Action log: 📄 Starting to process report report_test: Test Report
INFO - Action log: ✍️ Generating summary (auto-completes in 10s)...
```

**Result:** ✅ Context received and logged correctly

### Controller Spawn Verification
**Log Analysis:** Found workers spawned with full command:
```bash
statemachine examples/patient_records/config/patient-records.yaml \
  --machine-name patient_record_job_001 \
  --initial-context '{"job_id":"job_001","report_id":"report_1","report_title":"Patient Report 1","summary_text":"Processing report 1"}'
```

**Result:** ✅ Controller successfully passes context to workers

## Files Modified

### Source Code (4 files)
1. `src/statemachine_engine/actions/builtin/start_fsm_action.py`
   - Added context_vars parameter
   - Implemented variable extraction methods
   - Updated docstring with examples

2. `src/statemachine_engine/cli.py`
   - Added --initial-context argument
   - JSON parsing and context merging

3. `examples/patient_records/config/patient-records.yaml`
   - Changed initial_state to summarizing
   - Removed waiting_for_report state
   - Added context verification logging

4. `examples/patient_records/config/concurrent-controller.yaml`
   - Added context_vars to start_fsm action

### Tests (1 file)
5. `tests/actions/test_start_fsm_action.py`
   - Added 7 new tests for context passing

### Documentation (1 file)
6. `docs/context-passing-implementation-plan.md`
   - 734-line comprehensive implementation plan
   - Architecture decisions, data flow, test specs

### Diagrams (6 files)
7-12. Regenerated FSM diagrams for patient-records example

**Total:** 11 files changed, 411 insertions(+), 74 deletions(-)

## Git History

### Commits
1. **6b243ca** - "docs: add comprehensive context passing implementation plan"
   - Saved detailed implementation plan

2. **a295437** - "feat: implement context passing from controller to spawned workers"
   - Complete implementation with tests
   - All integration verified
   - Documentation updated

### Repository
- **Branch:** main
- **Remote:** github.com/sheikkinen/statemachine-engine
- **Status:** Pushed to GitHub ✅

## Current Status

### ✅ Completed
- [x] Investigation and root cause analysis
- [x] Implementation plan document created
- [x] TDD test suite (7 new tests, all passing)
- [x] StartFsmAction enhancement (context_vars)
- [x] CLI enhancement (--initial-context)
- [x] Worker FSM refactoring (auto-start)
- [x] Controller configuration update
- [x] Integration testing and verification
- [x] Documentation updates
- [x] Code committed and pushed to GitHub

### 🎯 Achievements
- Workers now receive job context immediately upon spawn
- Workers auto-start in processing state (no event needed)
- No test regressions (all 232 tests passing)
- Clean, testable, generic implementation
- Fully documented with examples

### 📊 Metrics
- **Test Coverage:** 18/18 StartFsmAction tests passing
- **Full Suite:** 232/241 tests (9 skipped)
- **Files Changed:** 11 files
- **Lines Changed:** +411/-74
- **Implementation Time:** ~1 session
- **Documentation:** 734-line plan + inline docstrings

## Technical Details

### Data Flow

```
Controller FSM (concurrent-controller)
  │
  ├─ check_database_queue action
  │   └─ Stores job in context.current_job
  │
  ├─ start_fsm action (context_vars specified)
  │   ├─ Extracts: current_job.id → job_id
  │   ├─ Extracts: report_id, report_title, summary_text
  │   └─ Serializes to JSON
  │
  └─ Spawns subprocess with --initial-context JSON
       │
       └─→ Worker FSM (patient-records)
            ├─ CLI parses --initial-context
            ├─ Merges into initial context
            ├─ Starts in 'summarizing' state
            └─ Logs: "🔍 Context verification - Job ID: ..."
```

### Context Variable Syntax

**Flat Variable:**
```yaml
context_vars:
  - job_id
```
Extracts `context['job_id']` → `{"job_id": "value"}`

**Nested Variable:**
```yaml
context_vars:
  - current_job.id
```
Extracts `context['current_job']['id']` → `{"id": "value"}`

**Renamed Variable:**
```yaml
context_vars:
  - current_job.id as job_id
```
Extracts `context['current_job']['id']` → `{"job_id": "value"}`

### Error Handling

**Missing Variables:**
- Logs warning: "Context variable 'xxx' not found in context"
- Continues execution (doesn't fail spawn)
- Worker receives partial context

**JSON Parse Error:**
- Logs error with details
- Uses empty context as fallback
- FSM continues with empty initial context

**Large Context:**
- Warns if JSON exceeds 4KB
- Continues with full context
- Suggests reducing variables if needed

## Usage Examples

### Basic Context Passing
```yaml
# Controller config
- type: start_fsm
  config:
    config_file: worker.yaml
    machine_name: worker_{job_id}
    context_vars:
      - job_id
      - task_name
```

### Nested and Renamed
```yaml
# Controller config
- type: start_fsm
  config:
    config_file: worker.yaml
    machine_name: worker_{current_job.id}
    context_vars:
      - current_job.id as job_id
      - current_job.data.task_name as task
      - priority
```

### Manual CLI Usage
```bash
# Direct worker spawn with context
statemachine worker.yaml \
  --machine-name my_worker \
  --initial-context '{"job_id":"job_123","priority":"high"}'
```

## Known Limitations

1. **Context Size:** 4KB warning threshold (CLI argument limit ~128KB on most systems)
2. **JSON Only:** Context must be JSON-serializable (no functions, objects with methods)
3. **One-Way:** Parent → Child only (no return values)
4. **No Nesting:** Dot notation limited to depth available in context dict

## Future Enhancements (Not Planned)

- Bi-directional context passing (child → parent)
- Context templates with variable substitution
- Encrypted context for sensitive data
- Context schema validation
- Auto-discovery of required context vars

## Lessons Learned

1. **TDD Prevents Regressions:** 7 new tests ensured no breaking changes to existing functionality
2. **CLI Debuggability:** JSON in command line visible in `ps aux` - invaluable for debugging
3. **Auto-Start Pattern:** Simpler than event-based triggering for spawn-to-process workflow
4. **Context Isolation:** Each worker gets only its job data - clean separation
5. **Graceful Degradation:** Missing variables log warnings but don't block execution

## References

- **Implementation Plan:** `docs/context-passing-implementation-plan.md`
- **StartFsmAction Code:** `src/statemachine_engine/actions/builtin/start_fsm_action.py`
- **CLI Code:** `src/statemachine_engine/cli.py`
- **Test Suite:** `tests/actions/test_start_fsm_action.py`
- **Example Config:** `examples/patient_records/config/concurrent-controller.yaml`

## Conclusion

The context passing implementation is **complete, tested, and deployed**. Workers now successfully receive job context from controllers and begin processing immediately upon spawn. The solution is generic, testable, and follows the project's architecture principles of being a library-first framework with no hard-coded domain logic.

**Status:** ✅ Ready for production use

---

*Document generated: November 8, 2025*  
*Commit: a295437*  
*Feature: Context Passing v1.0*
