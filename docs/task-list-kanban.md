# Kanban Implementation Task List (TDD)

## 🎯 Objective
Add Kanban view for concurrent FSM visualization - patient records demo with 10+ instances

## Initial Checklist
- [x] Patient records FSM created (`examples/patient_records/config/patient-records.yaml`)
- [x] State groups added for new diagram format (3 composite subdiagrams)
- [x] Demo script created (`examples/patient_records/run-demo.sh`)
- [x] Check Pytest and npm test suites pass before starting
- [x] Plan finalized with modular KanbanManager.js approach
- [x] Check that 10 concurrent instances run without errors: 10 machines processing simultaneously, ui starts with current fsm view
- [x] Database enhancement: config_type field for diagram mapping
- [x] Engine extracts config name from YAML and populates config_type
- [x] UI uses config_type for diagram loading (resolves patient_record_1 → patient_records mapping)

## Initialization Tasks
- [x] Add configurable instance count to demo script (default: 1, test with 10)
- [x] Add generic job initialization for all machines (job_1, job_2, etc.)
- [x] Send start event to all machines after initialization
- [x] Test single instance workflow end-to-end
- [x] Generate FSM diagrams automatically on demo start
- [x] Start UI server automatically (Node.js on port 3001)
- [x] Start WebSocket server automatically (port 3002)
- [x] Test 10 concurrent instances with job events
- [x] Verify UI shows all instances with correct states

**Initialization Complete!** All 10 machines running with generic job events (job_1..job_10).
Demo now includes automatic diagram generation and UI server startup.

## 🔴 RED: Write Tests First

### Test Files to Create
- [ ] Create `src/statemachine_engine/ui/public/tests/KanbanManager.test.js`
  - [ ] Test: KanbanManager constructor initializes correctly
  - [ ] Test: `detectBatchStates()` groups machines by FSM type
  - [ ] Test: `showKanbanModal()` displays modal with correct columns
  - [ ] Test: `updateInstance()` moves cards between columns
  - [ ] Test: `closeKanbanModal()` hides modal properly
  - [ ] Test: `_renderBoard()` creates CSS Grid layout
  - [ ] Test: `_createCard()` generates correct HTML structure
  - [ ] Test: `_animateCardMovement()` applies transition classes
  - [ ] Test: `_bindEvents()` attaches click handlers correctly

### Integration Tests
- [ ] Update existing test files with Kanban integration tests
  - [ ] Test: app-modular.js imports KanbanManager correctly
  - [ ] Test: Keyboard shortcut (K) triggers Kanban modal
  - [ ] Test: WebSocket state_change events update Kanban cards
  - [ ] Test: MachineStateManager provides correct batch data
  - [ ] Test: Modal doesn't interfere with existing diagram functionality

### Test Setup
- [ ] Add Kanban test data fixtures
  - [ ] Mock patient record instances (10+ machines)
  - [ ] Mock WebSocket state change events
  - [ ] Mock MachineStateManager batch data
- [ ] Add DOM test utilities for modal testing
- [ ] Add CSS transition test helpers
- [ ] Test. Test. Test. Ensure all tests fail initially (RED)

## 🟢 GREEN: Implement Minimum Code

### Step 1: Core Module (Minimum Implementation)
- [ ] Create `src/statemachine_engine/ui/public/modules/KanbanManager.js` 
  - [ ] Basic class constructor (pass failing tests)
  - [ ] Stub methods that return empty/default values
  - [ ] `detectBatchStates()` returns empty object
  - [ ] `showKanbanModal()` creates basic modal structure
  - [ ] `updateInstance()` basic card movement logic
  - [ ] `closeKanbanModal()` hides modal

### Step 2: UI Structure (Test-Required HTML)
- [ ] Update `src/statemachine_engine/ui/public/index.html`
  - [ ] Add minimal `#kanban-modal` div for tests
  - [ ] Add basic modal structure that tests expect

### Step 3: Basic Styling (Test-Required CSS)
- [ ] Update `src/statemachine_engine/ui/public/style.css`
  - [ ] Minimal modal visibility styles
  - [ ] Basic grid layout (1 column to start)
  - [ ] Card container styles for test recognition

### Step 4: Integration (Test-Required Connections)
- [ ] Update `src/statemachine_engine/ui/public/app-modular.js`
  - [ ] Import KanbanManager (even if methods are stubs)
  - [ ] Initialize in `initializeModules()` 
  - [ ] Add keyboard event listener (K key)

### Step 5: Extensions (Test-Required Data)
- [ ] Update `src/statemachine_engine/ui/public/modules/MachineStateManager.js`
  - [ ] Add stub methods that return test-friendly data
  - [ ] `groupInstancesByType()` returns grouped test data

## 🔵 REFACTOR: Enhance Implementation

### Full Feature Implementation
- [ ] Enhance KanbanManager methods with real logic
- [ ] Add proper CSS Grid layout with multiple columns
- [ ] Implement smooth animations and transitions
- [ ] Add proper error handling and edge cases
- [ ] Add responsive design and mobile support

### Performance & UX Improvements  
- [ ] Optimize card movement animations
- [ ] Add loading states for async operations
- [ ] Implement keyboard navigation within modal
- [ ] Add visual feedback for user interactions

## 🧪 Continuous Testing

### After Each TDD Cycle
- [ ] Run `npm test` - all tests should pass after GREEN phase
- [ ] Run patient records demo integration test
- [ ] Verify no regression in existing functionality
- [ ] Manual test keyboard shortcut (K) functionality

### End-to-End Testing
- [ ] Test with 10 concurrent patient record instances
- [ ] Verify real-time WebSocket updates move cards
- [ ] Test modal open/close with existing UI interactions
- [ ] Cross-browser compatibility check

## ✅ Success Criteria
- [ ] Keyboard shortcut (K) opens Kanban view for batch FSMs
- [ ] Cards animate smoothly between state columns
- [ ] Real-time updates from WebSocket events
- [ ] Zero breakage of existing functionality
- [ ] Demo runs with 10 concurrent patient record instances

## 🎮 TDD Demo Workflow

### Test-First Development Cycle
```bash
# 1. Write tests first
npm test  # Should FAIL initially (RED)

# 2. Write minimum code to pass tests  
npm test  # Should PASS after implementation (GREEN)

# 3. Refactor and improve
npm test  # Should still PASS after refactoring (REFACTOR)

# 4. Integration testing with demo
./examples/patient_records/run-demo.sh start
./examples/patient_records/run-demo.sh events
open http://localhost:3002  # Press K key to test

# 5. Cleanup
./examples/patient_records/run-demo.sh cleanup
```

### Test Development Order
1. **RED:** Write KanbanManager.test.js (tests fail)
2. **GREEN:** Create minimal KanbanManager.js (tests pass)
3. **REFACTOR:** Enhance implementation (tests still pass)
4. **REPEAT:** Next feature/method

## 📝 TDD Implementation Notes
- **Test-driven:** Every method has tests before implementation
- **Minimal viable:** Start with simplest passing implementation
- **Incremental:** Add one feature at a time with full test coverage
- **Refactor safely:** Tests ensure no regression during improvements
- **No backend changes** - use existing engine/database/WebSocket
- **Modular design** - separate module keeps DiagramManager.js clean