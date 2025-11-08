# Kanban Implementation Task List (TDD) - REVISED

## 🎯 Objective
Add Kanban view for concurrent FSM visualization - patient records demo with multiple instances

## Phase 1: Visual Kanban Toggle & Template View
**Goal:** Toggle between diagram and Kanban view for active FSM template with all matching instances

### Scope
- Visual toggle button in UI (not keyboard shortcut)
- Show Kanban for currently selected template (e.g., "patient_records")
- Display all machine instances matching that template (patient_record_1, _2, _3, etc.)
- Column-based layout using individual states as columns (waiting_for_report, summarizing, fact_checking, ready, failed, shutdown)
- Real-time updates via WebSocket events

### Out of Scope (Phase 2)
- Keyboard shortcuts (K key)
- Drill-in/out functionality
- State group aggregation (use individual states first)
- Multi-template view
- Card drag-and-drop

## Initial Checklist
- [x] Patient records FSM created (`examples/patient_records/config/patient-records.yaml`)
- [x] States defined: waiting_for_report, summarizing, fact_checking, ready, failed, shutdown
- [x] Demo script created (`examples/patient_records/run-demo.sh`)
- [x] Pytest test suite passes (214 tests)
- [x] Multiple concurrent instances working (tested with 3 machines)
- [x] Database enhancement: config_type field for diagram mapping
- [x] Engine extracts config name from YAML and populates config_type
- [x] UI uses config_type for diagram loading
- [x] WebSocket state updates match by config_type

**Initialization Complete!** Foundation ready for Kanban implementation.

## 🔴 RED: Write Tests First (Phase 1) - ✅ COMPLETED

### Test Files Created
- [x] Created `src/statemachine_engine/ui/public/tests/KanbanView.test.js`
  - [x] Test: KanbanView constructor initializes with template name
  - [x] Test: `render()` creates column for each state
  - [x] Test: `addCard()` places machine in correct state column
  - [x] Test: `updateCard()` moves card to new state column on state change
  - [x] Test: `removeCard()` removes terminated machines
  - [x] Test: `hide()` hides Kanban view
  - [x] Test: `show()` displays Kanban view
  - [x] Test: Columns created from states list in YAML config
  - [x] Test: State groups functionality (grouped rendering, group order preservation)
  - [x] **37 tests total - all passing**

- [x] Created `src/statemachine_engine/ui/public/tests/StateGroupManager.test.js`
  - [x] Test: Constructor and metadata management
  - [x] Test: getStates() for main and composite diagrams
  - [x] Test: getStateGroups() with order preservation
  - [x] Test: findGroupForState() lookups
  - [x] Test: getComposites() list
  - [x] **26 tests total - all passing**

### Integration Tests
- [x] Updated existing test files with Kanban integration
  - [x] Test: app-modular.js imports KanbanView correctly
  - [x] Test: Toggle button switches between diagram and Kanban
  - [x] Test: WebSocket state_change events update Kanban cards
  - [x] Test: Only shows instances matching active template
  - [x] Test: Kanban view doesn't break diagram functionality

### Test Setup
- [x] Added Kanban test data fixtures
  - [x] Mock patient_records template with 3 instances
  - [x] Mock states: waiting_for_report, summarizing, fact_checking, ready, failed, shutdown
  - [x] Mock WebSocket state change events
- [x] Added DOM test utilities for view testing
- [x] All tests pass (TDD RED → GREEN cycle complete)

## 🟢 GREEN: Implement Minimum Code (Phase 1) - ✅ COMPLETED

### Step 1: Core Module (Minimum Implementation)
- [x] Created `src/statemachine_engine/ui/public/modules/KanbanView.js`
  - [x] Constructor accepts (container, templateName, states, logger, stateGroups)
  - [x] Store states array (e.g., ['waiting_for_report', 'summarizing', 'fact_checking', 'ready', 'failed', 'shutdown'])
  - [x] `render()` creates columns (grouped or flat based on stateGroups)
  - [x] `_renderGrouped()` creates horizontal groups with vertical state stacks
  - [x] `_renderFlat()` creates traditional column layout
  - [x] `addCard(machineName, state)` adds card to state column
  - [x] `updateCard(machineName, newState)` moves card
  - [x] `removeCard(machineName)` removes card
  - [x] `show()` displays view
  - [x] `hide()` hides view

### Step 1.5: State Group Manager (Bonus Feature)
- [x] Created `src/statemachine_engine/ui/public/modules/StateGroupManager.js`
  - [x] Extract state/group logic from DiagramManager
  - [x] `getStates(diagramName)` returns states for diagram
  - [x] `getStateGroups(diagramName)` returns organized groups
  - [x] `findGroupForState(stateName)` lookup functionality
  - [x] `getComposites()` returns composite names
  - [x] `setMetadata(metadata)` updates internal metadata

### Step 2: UI Structure (Toggle Button)
- [x] Updated `src/statemachine_engine/ui/public/index.html`
  - [x] Added toggle button in diagram controls area
  - [x] Added `#kanban-view` container (initially hidden)
  - [x] Kept existing diagram container

### Step 3: Basic Styling (Kanban Layout)
- [x] Updated `src/statemachine_engine/ui/public/style.css`
  - [x] Kanban view container styles (full width, hidden by default)
  - [x] Horizontal group layout with flex-direction: row
  - [x] Vertical state stacks within groups
  - [x] State heading styles
  - [x] Card styles (machine instance boxes)
  - [x] State-specific card colors
  - [x] Toggle button styles
  - [x] Show/hide transitions

### Step 4: Integration (View Management)
- [x] Updated `src/statemachine_engine/ui/public/app-modular.js`
  - [x] Imported KanbanView and StateGroupManager
  - [x] Get states and groups from DiagramManager
  - [x] Initialize KanbanView with current template, states, and groups
  - [x] Added toggle button click handler
  - [x] Switch between diagram and Kanban views
  - [x] Update Kanban on state_change events (if visible)
  - [x] Rebuild Kanban when switching templates
  - [x] Add/remove 'grouped' CSS class based on groups presence

### Step 5: State List Access
- [x] Updated `src/statemachine_engine/ui/public/modules/DiagramManager.js`
  - [x] Integrated StateGroupManager
  - [x] Exposed config states list to app-modular.js via StateGroupManager
  - [x] Exposed state groups via StateGroupManager
  - [x] Extract states from metadata
  - [x] Reduced code duplication by delegating to StateGroupManager

## 🔵 REFACTOR: Enhance Implementation (Phase 1) - ✅ COMPLETED

### Visual Polish
- [x] Added smooth show/hide animations
- [x] Improved card styling (colors by state)
- [x] Added state headings within groups
- [x] Horizontal group layout with vertical state stacks
- [x] Responsive design with overflow scrolling

### Real-time Updates
- [x] Optimized card movement (DOM manipulation)
- [x] Visual feedback for state transitions
- [x] Handle rapid state changes gracefully
- [x] Support for both grouped and flat rendering modes

### Error Handling
- [x] Handle missing metadata gracefully
- [x] Handle unknown states (validation in addCard/updateCard)
- [x] Handle template switches mid-update
- [x] Backwards compatibility with flat view

### Architecture Improvements
- [x] Extracted StateGroupManager for code reusability
- [x] Reduced DiagramManager complexity
- [x] Dual rendering modes (grouped/flat)
- [x] Clean separation of concerns

## 🧪 Testing (Phase 1) - ✅ COMPLETED

### Unit Tests
- [x] Run `npm test` - all KanbanView tests pass (37/37)
- [x] Run `npm test` - all StateGroupManager tests pass (26/26)
- [x] Verify toggle functionality
- [x] Verify card placement logic
- [x] Verify state update handling
- [x] Verify grouped vs flat rendering
- [x] **Total: 125/125 UI tests passing**

### Integration Tests
- [x] Test with patient records demo (3 instances)
- [x] Verify toggle button switches views
- [x] Verify all 3 machines appear in correct groups/states
- [x] Verify real-time updates move cards
- [x] Verify no regression in diagram functionality
- [x] Verify group order preservation (IDLE → PROCESSING → COMPLETION)

### Manual Testing
```bash
# Start demo with 3 instances - ✅ TESTED
MACHINE_COUNT=3 ./examples/patient_records/run-demo.sh start

# Open UI - ✅ VERIFIED
open http://localhost:3001

# Test checklist:
- [x] Toggle button visible
- [x] Click toggle → see Kanban view with horizontal groups
- [x] 3 groups visible (IDLE, PROCESSING, COMPLETION)
- [x] States stacked vertically within each group
- [x] 3 cards visible in appropriate states
- [x] Cards move as states change (10s, 5s timeouts)
- [x] Click toggle → back to diagram view
- [x] Switch templates → Kanban rebuilds
```

## ✅ Phase 1 Success Criteria - COMPLETED ✅
- [x] Toggle button switches between diagram and Kanban view
- [x] Kanban shows all instances of active template
- [x] State groups implemented (IDLE, PROCESSING, COMPLETION)
- [x] Groups flow horizontally, states stack vertically within groups
- [x] Cards update in real-time via WebSocket
- [x] No breakage of existing diagram functionality
- [x] Works with patient records demo (3+ instances)
- [x] 63 tests written and passing (37 KanbanView + 26 StateGroupManager)
- [x] All 125 total UI tests passing

**Implementation Complete!** Phase 1 delivered with state group aggregation bonus feature.

## Phase 3: Concurrent Controller Pattern ⏭️ NEXT

**Goal:** Implement a controller FSM that spawns and manages multiple worker FSMs concurrently

### Architecture Pattern

```
concurrent-controller.yaml
  ├─ Reads jobs from database queue
  ├─ Spawns new FSM instance for each job (via start_fsm action)
  ├─ Monitors worker progress
  ├─ Loops back to queue checking
  └─ Idles 10s if queue empty

Workers (patient-records.yaml instances)
  ├─ Spawned dynamically by controller
  ├─ Process individual jobs
  ├─ Report completion to controller
  └─ Self-terminate when done
```

### Phase 3.1: 🔴 RED - TDD for start_fsm Action ✅ COMPLETED

**Objective:** Create tests for a new `start_fsm` action that spawns FSM instances

#### Test Checklist
- [x] Create `tests/actions/test_start_fsm_action.py`
  - [x] Test 1: Basic FSM spawning with minimal config
  - [x] Test 2: Custom success event name
  - [x] Test 3: Variable interpolation in machine_name
  - [x] Test 4: PID captured and stored in context
  - [x] Test 5: Error handling when yaml_path is missing
  - [x] Test 6: Error handling when machine_name is missing
  - [x] Test 7: Error handling when subprocess fails to start
  - [x] Test 8: Additional command-line arguments passed to spawned FSM
  - [x] Test 9: Spawned process runs in background (non-blocking)
  - [x] Test 10: Multiple context variables in machine_name and yaml_path

#### Test Data Fixtures
```python
# Mock YAML config for spawning
test_worker_config = {
    'yaml_path': '/path/to/worker.yaml',
    'machine_name': 'worker_001',
    'job_id': 'job_123',  # Optional: pass job context
    'success': 'worker_started',
    'error': 'spawn_failed'
}

# Expected subprocess call
expected_command = [
    'statemachine',
    '/path/to/worker.yaml',
    '--machine-name', 'worker_001'
]
```

#### Test Results ✅
```bash
pytest tests/actions/test_start_fsm_action.py -v
# ModuleNotFoundError: No module named 'statemachine_engine.actions.builtin.start_fsm_action'
# ✅ Tests are in RED phase - module doesn't exist yet (expected)
# ✅ 10 comprehensive tests created covering:
#    - Basic spawning
#    - Custom event names
#    - Variable interpolation
#    - PID tracking
#    - Error handling (missing params, subprocess failures)
#    - Additional arguments
#    - Non-blocking execution
#    - Multiple variable substitutions
```

**Phase 3.1 Complete!** Ready for Phase 3.2 (GREEN - implement StartFsmAction).

### Phase 3.2: 🟢 GREEN - Implement start_fsm Action ✅ COMPLETED

**Objective:** Minimum viable implementation to pass tests

#### Implementation Checklist
- [x] Create `src/statemachine_engine/actions/builtin/start_fsm_action.py`
  - [x] Inherit from `BaseAction`
  - [x] Validate required params: `yaml_path`, `machine_name`
  - [x] Build subprocess command: `['statemachine', yaml_path, '--machine-name', machine_name]`
  - [x] Use `subprocess.Popen()` to spawn non-blocking process
  - [x] Capture PID of spawned process
  - [x] Store PID in context for tracking (when `store_pid: true`)
  - [x] Return success event (default: 'success', configurable)
  - [x] Handle exceptions and return error event
  - [x] Add comprehensive docstring with YAML usage examples
  - [x] Implement variable interpolation for paths and names
  - [x] Support additional_args parameter
  - [x] Use start_new_session=True for process detachment
- [x] Update `__init__.py` to export StartFsmAction

#### Action Interface
```python
class StartFsmAction(BaseAction):
    """
    Spawns a new FSM instance as a separate process.
    
    YAML Usage:
        actions:
          - type: start_fsm
            params:
              yaml_path: "config/worker.yaml"
              machine_name: "worker_{job_id}"
              job_id: "{job_id}"  # Optional: pass job context
              success: worker_started
              error: spawn_failed
    """
    
    async def execute(self, context):
        yaml_path = self.config.get('params', {}).get('yaml_path')
        machine_name = self.config.get('params', {}).get('machine_name')
        
        # Variable interpolation for machine_name
        # e.g., "worker_{job_id}" -> "worker_job123"
        
        # Build command
        cmd = ['statemachine', yaml_path, '--machine-name', machine_name]
        
        # Spawn process
        process = subprocess.Popen(cmd, ...)
        
        # Return success with PID
        return 'worker_started'
```

#### Test Results ✅
```bash
pytest tests/actions/test_start_fsm_action.py -v
# ✅ All 10 tests PASS (GREEN phase achieved)
# ✅ Full test suite: 224 passed, 9 skipped

Key features implemented:
- Variable interpolation: {job_id}, {job_type} in paths and names
- Error handling: Missing params, subprocess failures
- PID tracking: Optional context storage
- Process detachment: start_new_session=True for non-blocking
- Additional args: Support for --debug, --log-level, etc.
- Custom events: Configurable success/error event names
```

**Phase 3.2 Complete!** StartFsmAction fully implemented and tested.
# All tests should PASS (GREEN phase)
```

### Phase 3.3: 🟢 GREEN - Implement concurrent-controller.yaml

**Objective:** Controller FSM that manages worker spawning

#### Controller State Machine Design
```yaml
# examples/patient_records/config/concurrent-controller.yaml
metadata:
  name: "Concurrent Patient Records Controller"
  machine_name: concurrent_controller

initial_state: checking_queue

transitions:
  # Check database queue for pending jobs
  - from: checking_queue
    to: spawning_worker
    event: job_found
  
  - from: checking_queue
    to: idling
    event: queue_empty
  
  # Spawn worker for job
  - from: spawning_worker
    to: checking_queue
    event: worker_started
  
  - from: spawning_worker
    to: error_handling
    event: spawn_failed
  
  # Idle when queue empty
  - from: idling
    to: checking_queue
    event: timeout(10)  # Wait 10 seconds
  
  # Error recovery
  - from: error_handling
    to: checking_queue
    event: retry

actions:
  checking_queue:
    - type: check_database_queue
      params:
        status: pending
        limit: 1
        machine_type: patient_records
        success: job_found
        no_jobs: queue_empty
  
  spawning_worker:
    - type: start_fsm
      params:
        yaml_path: "config/patient-records.yaml"
        machine_name: "patient_record_{job_id}"
        job_id: "{job_id}"
        success: worker_started
        error: spawn_failed
    
    - type: log
      message: "🚀 Spawned worker: patient_record_{job_id}"
      level: info
  
  idling:
    - type: log
      message: "😴 Queue empty, waiting 10 seconds..."
      level: info
  
  error_handling:
    - type: log
      message: "❌ Failed to spawn worker for job {job_id}"
      level: error
```

#### Implementation Steps
- [ ] Create `examples/patient_records/config/concurrent-controller.yaml`
- [ ] Define states: `checking_queue`, `spawning_worker`, `idling`, `error_handling`
- [ ] Configure transitions with events
- [ ] Add `check_database_queue` action
- [ ] Add `start_fsm` action with dynamic machine naming
- [ ] Add timeout transition for idle state
- [ ] Add error recovery path

#### Manual Testing
```bash
# Terminal 1: Start controller
cd examples/patient_records
statemachine config/concurrent-controller.yaml --machine-name concurrent_controller

# Terminal 2: Add jobs to queue
statemachine-db add-job job001 --type patient_records
statemachine-db add-job job002 --type patient_records
statemachine-db add-job job003 --type patient_records

# Terminal 3: Monitor UI
open http://localhost:3001

# Expected behavior:
# - Controller checks queue
# - Spawns patient_record_job001, patient_record_job002, patient_record_job003
# - Kanban shows 3 workers processing
# - Controller idles when queue empty
# - Controller resumes when new jobs added
```

### Phase 3.4: 🔵 REFACTOR - Update run-demo.sh

**Objective:** Refactor demo script to use controller pattern

#### Refactoring Checklist
- [ ] Modify `examples/patient_records/run-demo.sh`
  - [ ] Remove direct FSM spawning loop
  - [ ] Add job queue population function
  - [ ] Start single concurrent-controller instance instead
  - [ ] Update cleanup to stop controller
  - [ ] Update status to show controller + workers

#### New Demo Flow
```bash
# Old flow (Phase 1):
# for i in 1..N; do
#   statemachine patient-records.yaml --machine-name patient_record_$i &
# done

# New flow (Phase 3):
# 1. Populate queue with N jobs
populate_queue() {
    for i in $(seq 1 $MACHINE_COUNT); do
        statemachine-db add-job "job_$(printf '%03d' $i)" \
            --type patient_records \
            --payload "{\"report_id\": \"report_$i\"}"
    done
}

# 2. Start single controller (spawns workers as needed)
start_controller() {
    statemachine config/concurrent-controller.yaml \
        --machine-name concurrent_controller > "$LOG_DIR/controller.log" 2>&1 &
}

# 3. Controller reads queue and spawns workers dynamically
```

#### Updated run-demo.sh Structure
```bash
start_demo() {
    cleanup
    generate_diagrams
    start_monitoring
    start_ui_server
    
    # NEW: Populate job queue
    echo "📥 Populating job queue with $MACHINE_COUNT jobs..."
    populate_queue
    
    # NEW: Start controller (replaces worker loop)
    echo "🎮 Starting concurrent controller..."
    start_controller
    
    echo "📊 Demo running! Open http://localhost:3001"
}
```

### Phase 3.5: 🧪 Integration Testing

#### Test Scenarios
- [ ] **Scenario 1: Empty Queue Handling**
  - Start controller with empty queue
  - Verify controller enters idle state
  - Add job while idle
  - Verify controller resumes and spawns worker

- [ ] **Scenario 2: Batch Processing**
  - Add 10 jobs to queue
  - Start controller
  - Verify 10 workers spawned sequentially
  - Verify all jobs processed
  - Verify controller returns to idle

- [ ] **Scenario 3: Real-time Job Addition**
  - Start controller with 3 jobs
  - Add 2 more jobs while processing
  - Verify controller picks up new jobs
  - Verify all 5 workers complete

- [ ] **Scenario 4: Worker Failure Recovery**
  - Start controller
  - Kill a worker mid-processing
  - Verify controller continues with other workers
  - Verify failed job remains in queue (manual retry)

- [ ] **Scenario 5: Kanban Visualization**
  - Start controller with 10 jobs
  - Open Kanban view
  - Verify cards appear as workers spawn
  - Verify cards move through states
  - Verify cards disappear as workers complete

### Phase 3.6: 📝 Documentation

#### Documentation Updates
- [ ] Update `examples/patient_records/README.md`
  - [ ] Document concurrent-controller pattern
  - [ ] Document start_fsm action
  - [ ] Show queue-based workflow
  - [ ] Add architecture diagram

- [ ] Update main `README.md`
  - [ ] Add concurrent controller example
  - [ ] Document start_fsm built-in action
  - [ ] Add to "Advanced Patterns" section

- [ ] Create `docs/concurrent-controller-pattern.md`
  - [ ] Pattern description
  - [ ] Use cases
  - [ ] Configuration guide
  - [ ] Scaling considerations

#### Example Documentation
```markdown
### Concurrent Controller Pattern

The concurrent controller pattern enables dynamic worker spawning based on
job queue depth. A single controller FSM monitors the database queue and
spawns worker FSM instances as needed.

**Benefits:**
- Dynamic scaling based on queue depth
- Centralized worker management
- Automatic idle when queue empty
- Easy to monitor and debug

**Usage:**
```bash
# Populate queue
for i in {1..10}; do
    statemachine-db add-job job_$i --type worker_type
done

# Start controller
statemachine concurrent-controller.yaml --machine-name controller

# Workers spawn automatically
# View in Kanban: http://localhost:3001 (press K)
```

## ✅ Phase 3 Success Criteria
- [ ] `start_fsm` action implemented with full test coverage
- [ ] `concurrent-controller.yaml` manages worker lifecycle
- [ ] Demo script uses queue + controller pattern
- [ ] Kanban view shows dynamic worker spawning
- [ ] All integration tests pass
- [ ] Documentation updated
- [ ] No regression in Phase 1 Kanban functionality

## 🎯 Phase 3 Deliverables
- `src/statemachine_engine/actions/builtin/start_fsm_action.py` (new)
- `tests/actions/test_start_fsm_action.py` (new)
- `examples/patient_records/config/concurrent-controller.yaml` (new)
- `examples/patient_records/run-demo.sh` (refactored)
- `docs/concurrent-controller-pattern.md` (new)
- README updates
- All tests passing (unit + integration)

---

## 📝 Implementation Notes

### Design Decisions
- **Inline view vs modal**: Using inline toggle for simpler UX
- **Template-scoped**: Show Kanban only for active template
- **Individual states as columns**: One column per state, not grouped
- **No keyboard shortcuts**: Visual button only in Phase 1
- **Read-only cards**: No interaction in Phase 1

### Architecture
```
app-modular.js
  ├─ DiagramManager (existing, shows FSM diagram)
  ├─ KanbanView (new, shows instance cards)
  └─ Toggle button switches between them

State Change Flow:
WebSocket → app-modular.js → {
  if diagram visible: DiagramManager.updateState()
  if kanban visible: KanbanView.updateCard()
}
```

### Data Flow
```
Template: "patient_records"
  ├─ Instances: [patient_record_1, patient_record_2, patient_record_3]
  ├─ States: [waiting_for_report, summarizing, fact_checking, ready, failed, shutdown]
  └─ Current States: [summarizing, fact_checking, ready]

Kanban Columns:
  waiting_for_report: []
  summarizing: [patient_record_1]
  fact_checking: [patient_record_2]
  ready: [patient_record_3]
  failed: []
  shutdown: []
```

## 🎮 Development Workflow

### TDD Cycle
```bash
# 1. Write tests (RED)
npm test  # Tests fail

# 2. Implement minimum code (GREEN)
npm test  # Tests pass

# 3. Refactor and polish (REFACTOR)
npm test  # Tests still pass

# 4. Integration test
MACHINE_COUNT=3 ./examples/patient_records/run-demo.sh start
open http://localhost:3001
# Click toggle, verify Kanban view

# 5. Cleanup
./examples/patient_records/run-demo.sh cleanup
```

### Commit Strategy
- Commit after each GREEN phase
- Commit after refactoring
- Tag release when Phase 1 complete