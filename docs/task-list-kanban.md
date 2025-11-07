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

## Phase 2: Enhanced Kanban Features (Future)

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