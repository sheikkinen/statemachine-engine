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

## 🔴 RED: Write Tests First (Phase 1)

### Test Files to Create
- [ ] Create `src/statemachine_engine/ui/public/tests/KanbanView.test.js`
  - [ ] Test: KanbanView constructor initializes with template name
  - [ ] Test: `render()` creates column for each state
  - [ ] Test: `addCard()` places machine in correct state column
  - [ ] Test: `updateCard()` moves card to new state column on state change
  - [ ] Test: `removeCard()` removes terminated machines
  - [ ] Test: `hide()` hides Kanban view
  - [ ] Test: `show()` displays Kanban view
  - [ ] Test: Columns created from states list in YAML config

### Integration Tests
- [ ] Update existing test files with Kanban integration
  - [ ] Test: app-modular.js imports KanbanView correctly
  - [ ] Test: Toggle button switches between diagram and Kanban
  - [ ] Test: WebSocket state_change events update Kanban cards
  - [ ] Test: Only shows instances matching active template
  - [ ] Test: Kanban view doesn't break diagram functionality

### Test Setup
- [ ] Add Kanban test data fixtures
  - [ ] Mock patient_records template with 3 instances
  - [ ] Mock states: waiting_for_report, summarizing, fact_checking, ready, failed, shutdown
  - [ ] Mock WebSocket state change events
- [ ] Add DOM test utilities for view testing
- [ ] Ensure all tests fail initially (RED)

## 🟢 GREEN: Implement Minimum Code (Phase 1)

### Step 1: Core Module (Minimum Implementation)
- [ ] Create `src/statemachine_engine/ui/public/modules/KanbanView.js`
  - [ ] Constructor accepts (container, templateName, states, logger)
  - [ ] Store states array (e.g., ['waiting_for_report', 'summarizing', 'fact_checking', 'ready', 'failed', 'shutdown'])
  - [ ] `render()` creates one column per state
  - [ ] `addCard(machineName, state)` adds card to state column
  - [ ] `updateCard(machineName, newState)` moves card
  - [ ] `removeCard(machineName)` removes card
  - [ ] `show()` displays view
  - [ ] `hide()` hides view

### Step 2: UI Structure (Toggle Button)
- [ ] Update `src/statemachine_engine/ui/public/index.html`
  - [ ] Add toggle button in diagram controls area
  - [ ] Add `#kanban-view` container (initially hidden)
  - [ ] Keep existing diagram container

### Step 3: Basic Styling (Kanban Layout)
- [ ] Update `src/statemachine_engine/ui/public/style.css`
  - [ ] Kanban view container styles (full width, hidden by default)
  - [ ] Column layout using CSS Grid (6 columns for 6 states)
  - [ ] Card styles (machine instance boxes)
  - [ ] Toggle button styles
  - [ ] Show/hide transitions

### Step 4: Integration (View Management)
- [ ] Update `src/statemachine_engine/ui/public/app-modular.js`
  - [ ] Import KanbanView
  - [ ] Get states list from config YAML or metadata
  - [ ] Initialize KanbanView with current template and states
  - [ ] Add toggle button click handler
  - [ ] Switch between diagram and Kanban views
  - [ ] Update Kanban on state_change events (if visible)
  - [ ] Rebuild Kanban when switching templates

### Step 5: State List Access
- [ ] Update `src/statemachine_engine/ui/public/modules/DiagramManager.js`
  - [ ] Expose config states list to app-modular.js
  - [ ] Or extract states from metadata if not available directly

## 🔵 REFACTOR: Enhance Implementation (Phase 1)

### Visual Polish
- [ ] Add smooth show/hide animations
- [ ] Improve card styling (colors by state)
- [ ] Add column headers with instance counts
- [ ] Add empty state message ("No instances running")

### Real-time Updates
- [ ] Optimize card movement animations
- [ ] Add visual feedback for state transitions
- [ ] Handle rapid state changes gracefully

### Error Handling
- [ ] Handle missing metadata gracefully
- [ ] Handle unknown states (put in default column)
- [ ] Handle template switches mid-update

## 🧪 Testing (Phase 1)

### Unit Tests
- [ ] Run `npm test` - all KanbanView tests pass
- [ ] Verify toggle functionality
- [ ] Verify card placement logic
- [ ] Verify state update handling

### Integration Tests
- [ ] Test with patient records demo (3 instances)
- [ ] Verify toggle button switches views
- [ ] Verify all 3 machines appear in correct columns
- [ ] Verify real-time updates move cards
- [ ] Verify no regression in diagram functionality

### Manual Testing
```bash
# Start demo with 3 instances
./examples/patient_records/run-demo.sh cleanup
MACHINE_COUNT=3 ./examples/patient_records/run-demo.sh start

# Open UI
open http://localhost:3001

# Test checklist:
- [ ] Toggle button visible
- [ ] Click toggle → see Kanban view
- [ ] 3 cards visible in columns
- [ ] Cards move as states change (10s, 5s timeouts)
- [ ] Click toggle → back to diagram view
- [ ] Switch templates → Kanban rebuilds
```

## ✅ Phase 1 Success Criteria
- [ ] Toggle button switches between diagram and Kanban view
- [ ] Kanban shows all instances of active template
- [ ] One column per state (6 columns for patient_records)
- [ ] Cards update in real-time via WebSocket
- [ ] No breakage of existing diagram functionality
- [ ] Works with patient records demo (3+ instances)

## Phase 2: State Group Aggregation (Future)

### Planned Features
- [ ] Group states into composite columns (IDLE, PROCESSING, COMPLETION)
- [ ] Click column header to expand/collapse states
- [ ] Drill-in to show subdiagram for state group
- [ ] Click composite state in diagram → show Kanban for that group
- [ ] Breadcrumb navigation between views
- [ ] Keyboard shortcuts (K key, ESC key)
- [ ] Multi-template aggregation view
- [ ] Card drag-and-drop for manual state changes

### Not Implemented Yet
- State group aggregation (showing individual states instead)
- Modal-based Kanban (using inline view instead)
- Batch state detection (showing template explicitly)
- Click handlers on cards (future enhancement)

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