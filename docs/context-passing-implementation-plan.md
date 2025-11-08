# Context Passing Implementation Plan

**Date**: 2025-11-08  
**Feature**: Pass job context from controller to spawned worker FSMs  
**Approach**: Mix of Option 1 (auto-start) + Option 3 (context-based initialization)

## Problem Statement

Worker FSMs spawned by concurrent-controller are stuck in `waiting_for_report` initial state because:

1. Workers start in `waiting_for_report` expecting a `new_report` event
2. Controller spawns workers but never sends the trigger event
3. Jobs marked as "processing" in database but never complete
4. Workers lack job context (job_id, report_id, etc.) needed for processing

### Current State
```
✅ Controller running (PID 13379) - idling, checking queue every 10s
✅ Workers spawned (PIDs 13381, 13382, 13383) - alive but stuck
❌ Workers in waiting_for_report state - need new_report event
❌ Jobs marked "processing" in DB - never complete
❌ No worker log files created - workers haven't entered action states yet
```

## Architecture Decision

### Chosen Approach: Command-line JSON argument (`--initial-context`)

**Rationale**:
- ✅ Clean separation: Context is explicit in process args
- ✅ Debuggable: Can see context in `ps aux` output
- ✅ Simple implementation: No IPC complexity
- ✅ Idempotent: Same spawn = same context
- ✅ Testable: Easy to mock and verify
- ❌ Arg length limit: Not an issue for typical job metadata (~500 bytes)
- ❌ Security: Context visible in process list (acceptable for job IDs)

### Rejected Alternatives

1. **Environment variables**: 
   - ❌ Pollutes environment namespace
   - ❌ Inheritance issues with child processes
   - ❌ Limited size, awkward for nested data

2. **Unix socket message after spawn**: 
   - ❌ Race condition: FSM may start before message arrives
   - ❌ Complexity: Requires handshake protocol
   - ❌ Unreliable: Message could be lost

3. **Temporary file**: 
   - ❌ Cleanup complexity
   - ❌ Race conditions on file access
   - ❌ Security concerns with temp files

## Data Flow

### Controller Context Structure
```python
{
  'current_job': {
    'id': 'job_001',
    'source_job_id': None,
    'job_type': 'patient_records',
    'data': {
      'report_id': 'report_1',
      'report_title': 'Patient Report 1',
      'summary_text': 'Processing report 1'
    }
  },
  # Flattened from current_job.data by engine:
  'report_id': 'report_1',
  'report_title': 'Patient Report 1',
  'summary_text': 'Processing report 1',
  'job_model': <JobModel instance>
}
```

### Context Extraction & Transformation
```yaml
# concurrent-controller.yaml
spawning_worker:
  - type: start_fsm
    context_vars:
      - current_job.id as job_id     # Rename: nested → flat
      - report_id                     # Pass through
      - report_title                  # Pass through
      - summary_text                  # Pass through
```

### Subprocess Command
```bash
statemachine examples/patient_records/config/patient-records.yaml \
  --machine-name patient_record_job_001 \
  --initial-context '{"job_id":"job_001","report_id":"report_1","report_title":"Patient Report 1","summary_text":"Processing report 1"}'
```

### Worker Initial Context
```python
{
  'job_id': 'job_001',              # From controller context
  'report_id': 'report_1',          # From controller context
  'report_title': 'Patient Report 1', # From controller context
  'summary_text': 'Processing report 1', # From controller context
  'job_model': <JobModel instance>   # Injected by CLI
}
```

### Worker Execution
```python
# Initial state: summarizing (auto-start)
# Log action: "📄 Starting to process report {report_id}: {report_title}"
# Output: "📄 Starting to process report report_1: Patient Report 1"
```

## Implementation Steps

### Phase 1: Extend CLI to Accept Initial Context

**File**: `src/statemachine_engine/cli.py`

**Changes**:
1. Add `--initial-context` argument to argparse
2. Parse JSON string into dict
3. Merge with existing `initial_context` dict
4. Handle JSON parse errors gracefully

```python
# In async_main()
parser.add_argument('--initial-context', 
                    help='JSON string with initial context variables',
                    default='{}')

# In run_state_machine()
try:
    user_context = json.loads(initial_context_json)
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON in --initial-context: {e}")
    return 1

initial_context = {
    'job_model': get_job_model(),
    **user_context  # Merge user context
}
```

**Tests**:
- Valid JSON parsing
- Invalid JSON error handling
- Empty string defaults to {}
- Context merges with job_model

### Phase 2: Update StartFsmAction with context_vars

**File**: `src/statemachine_engine/actions/builtin/start_fsm_action.py`

**New Parameter**: `context_vars` (list of strings or dicts)

**Syntax Support**:
```yaml
context_vars:
  - simple_var                    # Copy as-is
  - nested.var                    # Extract nested value
  - nested.var as renamed_var     # Extract + rename
```

**Implementation**:
```python
def __init__(self, config: Dict[str, Any]):
    # ... existing code ...
    self.context_vars = config.get('context_vars', [])

def _extract_context_vars(self, context: Dict[str, Any]) -> Dict[str, Any]:
    """Extract specified variables from context"""
    extracted = {}
    
    for var_spec in self.context_vars:
        # Parse "source as target" or just "source"
        if ' as ' in var_spec:
            source, target = var_spec.split(' as ', 1)
            source = source.strip()
            target = target.strip()
        else:
            source = target = var_spec.strip()
        
        # Extract value (supports dot notation)
        value = self._get_nested_value(context, source)
        
        if value is not None:
            extracted[target] = value
        else:
            logger.warning(f"Context variable '{source}' not found, skipping")
    
    return extracted

def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
    """Get value from nested dict using dot notation"""
    keys = path.split('.')
    value = data
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    
    return value

async def execute(self, context: Dict[str, Any]) -> str:
    # ... existing validation ...
    
    # Extract context variables if specified
    if self.context_vars:
        context_data = self._extract_context_vars(context)
        
        # Serialize to JSON
        try:
            context_json = json.dumps(context_data, separators=(',', ':'))
            
            # Warn if too large (>4KB)
            if len(context_json) > 4096:
                logger.warning(f"Context JSON is large ({len(context_json)} bytes)")
            
            # Add to command
            command.extend(['--initial-context', context_json])
            
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize context: {e}")
            return self.get_config_value('error', 'error')
    
    # ... rest of existing code ...
```

**Tests**:
- Extract flat variable
- Extract nested variable with dot notation
- Rename variable with "as" syntax
- Handle missing variables gracefully
- JSON serialization
- Command construction with --initial-context
- Large context warning (>4KB)

### Phase 3: Update Worker FSM Configuration

**File**: `examples/patient_records/config/patient-records.yaml`

**Changes**:
1. Change `initial_state` from `waiting_for_report` to `summarizing`
2. Update log messages to use flat context vars
3. Add verification log showing received context

```yaml
name: "patient-records"
initial_state: summarizing  # Changed from waiting_for_report

states:
  # === SUMMARIZING ===
  - summarizing
  # === FACT_CHECKING ===
  - fact_checking
  # === COMPLETED ===
  - ready
  - failed
  - shutdown

transitions:
  # Auto-transitions for processing
  - from: summarizing
    to: fact_checking
    event: timeout(10)
  
  # ... rest unchanged ...

actions:
  summarizing:
    - type: log
      message: "🔍 Context verification - Job ID: {job_id}, Report: {report_id} ({report_title})"
      level: info
    - type: log
      message: "📄 Starting to process report {report_id}: {report_title}"
      level: info
    - type: log
      message: "✍️ Generating summary (auto-completes in 10s)..."
      level: info

  # ... rest unchanged ...
```

**Note**: Remove `waiting_for_report` state and `new_report` event (no longer needed)

### Phase 4: Update Controller Configuration

**File**: `examples/patient_records/config/concurrent-controller.yaml`

**Changes**: Add `context_vars` to `start_fsm` action

```yaml
spawning_worker:
  - type: log
    message: "🚀 Spawning worker for job: {current_job.id}"
    level: info
  
  - type: start_fsm
    yaml_path: "examples/patient_records/config/patient-records.yaml"
    machine_name: "patient_record_{current_job.id}"
    context_vars:
      - current_job.id as job_id      # Extract job ID from nested structure
      - report_id                      # Pass flattened job data
      - report_title                   # Pass flattened job data
      - summary_text                   # Pass flattened job data
    success: worker_started
    error: spawn_failed
    store_pid: true
  
  - type: log
    message: "✅ Worker spawned: patient_record_{current_job.id}"
    level: success
```

### Phase 5: TDD Test Suite

**File**: `tests/actions/test_start_fsm_action.py`

**New Tests**:

```python
@pytest.mark.asyncio
async def test_start_fsm_with_context_vars():
    """Test basic context variable extraction and passing"""
    context = {
        'job_id': 'job_001',
        'report_id': 'report_1',
        'report_title': 'Test Report'
    }
    
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_001',
        'context_vars': ['job_id', 'report_id', 'report_title']
    }
    
    action = StartFsmAction(config)
    
    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value.pid = 12345
        result = await action.execute(context)
        
        # Verify command includes --initial-context
        call_args = mock_popen.call_args[0][0]
        assert '--initial-context' in call_args
        
        # Parse and verify JSON
        ctx_idx = call_args.index('--initial-context') + 1
        context_json = json.loads(call_args[ctx_idx])
        
        assert context_json == {
            'job_id': 'job_001',
            'report_id': 'report_1',
            'report_title': 'Test Report'
        }
        assert result == 'success'


@pytest.mark.asyncio
async def test_start_fsm_with_nested_context_vars():
    """Test nested variable extraction with dot notation"""
    context = {
        'current_job': {
            'id': 'job_001',
            'type': 'patient_records'
        },
        'report_id': 'report_1'
    }
    
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_001',
        'context_vars': ['current_job.id', 'current_job.type', 'report_id']
    }
    
    action = StartFsmAction(config)
    
    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value.pid = 12345
        result = await action.execute(context)
        
        call_args = mock_popen.call_args[0][0]
        ctx_idx = call_args.index('--initial-context') + 1
        context_json = json.loads(call_args[ctx_idx])
        
        assert context_json == {
            'current_job.id': 'job_001',
            'current_job.type': 'patient_records',
            'report_id': 'report_1'
        }


@pytest.mark.asyncio
async def test_start_fsm_with_renamed_context_vars():
    """Test variable renaming with 'as' syntax"""
    context = {
        'current_job': {'id': 'job_001'},
        'long_variable_name': 'value'
    }
    
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_001',
        'context_vars': [
            'current_job.id as job_id',
            'long_variable_name as short'
        ]
    }
    
    action = StartFsmAction(config)
    
    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value.pid = 12345
        result = await action.execute(context)
        
        call_args = mock_popen.call_args[0][0]
        ctx_idx = call_args.index('--initial-context') + 1
        context_json = json.loads(call_args[ctx_idx])
        
        # Verify renamed keys
        assert context_json == {
            'job_id': 'job_001',
            'short': 'value'
        }


@pytest.mark.asyncio
async def test_start_fsm_missing_context_vars():
    """Test graceful handling of missing variables"""
    context = {
        'existing_var': 'value'
    }
    
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_001',
        'context_vars': ['existing_var', 'missing_var', 'also.missing']
    }
    
    action = StartFsmAction(config)
    
    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value.pid = 12345
        result = await action.execute(context)
        
        # Should succeed with partial context
        call_args = mock_popen.call_args[0][0]
        ctx_idx = call_args.index('--initial-context') + 1
        context_json = json.loads(call_args[ctx_idx])
        
        # Only existing var included
        assert context_json == {'existing_var': 'value'}
        assert result == 'success'


@pytest.mark.asyncio
async def test_start_fsm_empty_context_vars():
    """Test with no context_vars specified"""
    context = {'some': 'data'}
    
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_001'
        # No context_vars
    }
    
    action = StartFsmAction(config)
    
    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value.pid = 12345
        await action.execute(context)
        
        # Verify no --initial-context arg
        call_args = mock_popen.call_args[0][0]
        assert '--initial-context' not in call_args


@pytest.mark.asyncio
async def test_start_fsm_large_context_warning():
    """Test warning for large context (>4KB)"""
    context = {
        'large_data': 'x' * 5000  # >4KB
    }
    
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_001',
        'context_vars': ['large_data']
    }
    
    action = StartFsmAction(config)
    
    with patch('subprocess.Popen') as mock_popen:
        mock_popen.return_value.pid = 12345
        
        with patch('logging.Logger.warning') as mock_warning:
            await action.execute(context)
            
            # Verify warning was logged
            mock_warning.assert_called()
            warning_msg = str(mock_warning.call_args[0][0])
            assert 'large' in warning_msg.lower()
```

### Phase 6: Integration Testing

**Test Procedure**:

1. Stop current demo:
   ```bash
   bash run-demo.sh cleanup
   ```

2. Start with 2 jobs:
   ```bash
   MACHINE_COUNT=2 bash run-demo.sh start
   ```

3. Check worker logs:
   ```bash
   tail -f logs/patient_record_job_001.log
   tail -f logs/patient_record_job_002.log
   ```

**Expected Output**:
```
2025-11-08 07:15:00 - INFO - [patient_record_job_001] Starting state machine
2025-11-08 07:15:00 - INFO - [patient_record_job_001] Initial state: summarizing
2025-11-08 07:15:00 - INFO - [patient_record_job_001] 🔍 Context verification - Job ID: job_001, Report: report_1 (Patient Report 1)
2025-11-08 07:15:00 - INFO - [patient_record_job_001] 📄 Starting to process report report_1: Patient Report 1
2025-11-08 07:15:00 - INFO - [patient_record_job_001] ✍️ Generating summary (auto-completes in 10s)...
2025-11-08 07:15:10 - INFO - [patient_record_job_001] summarizing --timeout(10)--> fact_checking
...
```

4. Verify jobs complete:
   ```bash
   statemachine-db list
   ```

**Expected**: Jobs show "completed" status

5. Check process args contain context:
   ```bash
   ps aux | grep patient_record_job
   ```

**Expected**: See `--initial-context '{"job_id":"job_001",...}'` in output

## Configuration Examples

### Minimal Example
```yaml
actions:
  spawn_worker:
    - type: start_fsm
      yaml_path: "worker.yaml"
      machine_name: "worker_1"
      context_vars:
        - job_id
```

### Full Example with Renaming
```yaml
actions:
  spawn_worker:
    - type: start_fsm
      yaml_path: "config/{job_type}_worker.yaml"
      machine_name: "worker_{job_type}_{job_id}"
      context_vars:
        - current_job.id as job_id           # Nested + rename
        - current_job.type as job_type       # Nested + rename
        - input_path                          # Flat variable
        - output_path                         # Flat variable
        - config.max_retries as max_retries  # Deep nested + rename
      success: worker_spawned
      error: spawn_failed
      store_pid: true
```

### Worker FSM Using Context
```yaml
name: "worker"
initial_state: processing

actions:
  processing:
    - type: log
      message: "Processing job {job_id} - input: {input_path}"
    - type: bash
      command: "process_file {input_path} {output_path}"
      timeout: 300
```

## Benefits

1. **Auto-start workers**: No manual event trigger needed
2. **Context isolation**: Each worker gets only its job data  
3. **Debuggable**: Context visible in `ps aux` output
4. **Flexible**: Controller decides what to pass
5. **Type-safe**: JSON serialization validates data structure
6. **Testable**: Easy to mock subprocess and verify args
7. **Backward compatible**: Existing FSMs without context_vars work unchanged

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Context too large for command line | Spawn fails | Warn if >4KB, document 32KB limit |
| Sensitive data in context | Security issue | Document concern, advise encryption for sensitive jobs |
| JSON serialization fails | Spawn fails | Catch exception, log error, return spawn_failed event |
| Variable not found in context | Partial context | Log warning, continue with available vars |
| Malformed 'as' syntax | Parse error | Validate format, log error, skip var |
| Race condition on context read | Wrong data | JSON is atomic, parsed before exec |

## Performance Considerations

- **Context extraction**: O(n) where n = number of context_vars (typically <10)
- **JSON serialization**: O(m) where m = size of context data (typically <1KB)
- **Command line parsing**: O(1) overhead, handled by argparse
- **Memory overhead**: ~1KB per spawned worker (context copy)

**Expected overhead**: <1ms per spawn, negligible for typical use cases

## Security Considerations

### Process List Visibility
Context data is visible in `ps aux` output. Avoid passing:
- Passwords or API keys
- Personal identifiable information (PII)
- Financial data

**Safe to pass**:
- Job IDs (opaque identifiers)
- File paths (if non-sensitive)
- Configuration flags
- Metadata (types, statuses)

### Recommendation
Store sensitive data in database, pass only job_id. Worker fetches sensitive data after spawn.

## Documentation Updates

### StartFsmAction Docstring
```python
"""
Action to spawn a new FSM instance with optional context passing.

YAML Usage:
    actions:
      - type: start_fsm
        yaml_path: "config/worker.yaml"
        machine_name: "worker_{job_id}"
        context_vars:
          - current_job.id as job_id    # Extract nested, rename
          - report_id                    # Pass flat variable
          - report_title                 # Pass flat variable
        success: worker_started
        error: spawn_failed

Context Variables:
    Supports three syntaxes:
    1. Flat: "variable_name" - Copy as-is
    2. Nested: "parent.child.field" - Extract using dot notation
    3. Renamed: "source as target" - Extract and rename

    Missing variables are logged as warnings but don't fail the spawn.
"""
```

### CLI Help
```
--initial-context JSON
    JSON string with initial context variables. Used by controller
    FSMs to pass job data to spawned workers.
    
    Example: '{"job_id":"job_001","report_id":"report_1"}'
```

## Testing Checklist

- [ ] Unit tests for context extraction (flat, nested, renamed)
- [ ] Unit tests for JSON serialization
- [ ] Unit tests for command construction
- [ ] Unit tests for missing variables
- [ ] Unit tests for empty context_vars
- [ ] Unit tests for large context warning
- [ ] Integration test: spawn with context
- [ ] Integration test: worker receives context
- [ ] Integration test: worker logs context vars
- [ ] Integration test: job completes successfully
- [ ] Integration test: multiple workers with different contexts
- [ ] Regression test: existing FSMs without context_vars work

## Success Criteria

1. ✅ Workers spawn and auto-start processing
2. ✅ Workers receive correct job context (job_id, report_id, etc.)
3. ✅ Workers log context variables on startup
4. ✅ Jobs transition from pending → processing → completed
5. ✅ No stuck jobs in "processing" state
6. ✅ All existing tests pass (235 total)
7. ✅ New tests pass (7 additional)
8. ✅ Demo completes successfully with MACHINE_COUNT=3

## Rollback Plan

If implementation causes issues:

1. Revert CLI changes (remove --initial-context)
2. Revert StartFsmAction changes (remove context_vars)
3. Change patient-records.yaml initial_state back to waiting_for_report
4. Add manual event sender after spawn (quick fix)

## Future Enhancements

1. **Context validation**: Schema validation for passed context
2. **Encrypted context**: Support for sensitive data passing
3. **Context templates**: Predefined context mappings for common patterns
4. **Bidirectional context**: Worker can update parent context (via events)
5. **Context persistence**: Store context in database for debugging

## References

- Original investigation: `docs/context-passing-investigation.md`
- StartFsmAction: `src/statemachine_engine/actions/builtin/start_fsm_action.py`
- Engine CLI: `src/statemachine_engine/cli.py`
- Test suite: `tests/actions/test_start_fsm_action.py`
- Demo config: `examples/patient_records/config/concurrent-controller.yaml`
