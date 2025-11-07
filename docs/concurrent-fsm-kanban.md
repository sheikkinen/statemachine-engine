# Concurrent FSM Kanban Plan

## Use Case: Patient Journal Summarization

**Workflow Steps:**
1. Convert report into paragraph
2. Check that paragraph is based on report, loop if not
3. Generate full history from paragraphs  
4. Check the history details are based on paragraphs, loop if not

**Challenge:** Simple FSM UI works great for single instances, but we need to visualize tens or hundreds of concurrent report processing operations.

## Recommended Approach: Hierarchical Kanban View

### Level 0: Machine Overview (Current UI)
- Keep existing single-FSM Mermaid diagram view
- Add aggregate progress indicators for batch processing states
- Show "Process Reports (85/100)" instead of simple state names

### Level 1: Kanban Pipeline View (New)
- Click on batch processing state opens Kanban modal/view
- Columns = FSM states: `Queue | Summarizing | Fact-Check | Failed | Ready`
- Cards = Individual reports with ID and progress
- Real-time animation as cards move between columns
- Visual bottleneck identification

### Level 2: Instance Detail (Enhanced)
- Click individual card shows single FSM diagram
- Error logs and retry options for failed instances
- Standard Mermaid view with highlighted current state

## Implementation Plan - Minimal Changes

### Task 1: Create Demo FSM
**File:** `examples/patient_records/config/patient-records.yaml`
- [x] Simple 4-state FSM for report processing
- [x] Demonstrates concurrent instance capability
- [x] Includes loop transitions for validation failures

### Task 2: UI Extensions (Minimal Impact)
**Files to modify:**
- [ ] `src/statemachine_engine/ui/public/index.html` - Add Kanban modal HTML structure
- [ ] `src/statemachine_engine/ui/public/modules/KanbanManager.js` - **NEW MODULE** for Kanban functionality
- [ ] `src/statemachine_engine/ui/public/app-modular.js` - Integrate KanbanManager
- [ ] `src/statemachine_engine/ui/public/style.css` - Add Kanban board styles

**Approach:**
- Create dedicated `KanbanManager.js` module (DiagramManager.js is already 800+ lines)
- Reuse existing WebSocket events and machine state tracking
- Add Kanban view as overlay/modal, don't replace main diagram
- Use existing `MachineStateManager` to track instance states
- Minimal JavaScript - leverage CSS Grid for Kanban layout

### Task 3: Backend Extensions (Zero Changes)
**No changes needed to core engine** - leverage existing capabilities:
- Multiple machine instances already supported
- WebSocket events already broadcast state changes
- Database already tracks individual machine states
- Job queue already handles concurrent processing

## File-Level Implementation Tasks

### 🎯 `examples/patient_records/config/patient-records.yaml`
```yaml
# TODO: Create simple FSM demo
# - 4 states: waiting, summarizing, fact_checking, completed
# - Loop transitions for validation failures  
# - Use log actions to simulate processing
# - Support 10+ concurrent instances via machine naming
```

### 🎯 `src/statemachine_engine/ui/public/index.html`
```html
<!-- TODO: Add Kanban modal structure -->
<!-- - Hidden modal div with Kanban board layout -->
<!-- - Close button and overlay -->
<!-- - Column headers and card containers -->
<!-- - Leverage existing CSS classes where possible -->
```

### 🎯 `src/statemachine_engine/ui/public/modules/KanbanManager.js` ⭐ NEW MODULE
```javascript
// TODO: Create dedicated Kanban management module
// - KanbanManager class with clean API
// - detectBatchStates(machines) - identify FSM types with multiple instances
// - showKanbanModal(fsmType) - display Kanban view for FSM type
// - renderKanbanBoard(instances) - populate columns with instance cards
// - updateCard(machineName, newState) - move card between columns
// - bindKanbanEvents() - click handlers for cards and modal
// - closeKanbanModal() - return to main diagram view
// - Minimal dependencies - only needs MachineStateManager data
```

### 🎯 `src/statemachine_engine/ui/public/app-modular.js`
```javascript
// TODO: Integrate KanbanManager
// - Import KanbanManager module
// - Initialize kanbanManager in initializeModules()
// - Add batch state detection to state_change handler
// - Pass machine updates to KanbanManager
// - Add keyboard shortcut (K key) to toggle Kanban view
```

### 🎯 `src/statemachine_engine/ui/public/style.css`
```css
/* TODO: Add Kanban board styles */
/* - Modal overlay and container */
/* - CSS Grid layout for columns */
/* - Card styling with hover effects */
/* - Animation classes for smooth transitions */
/* - Responsive design for mobile viewing */
```

### 🎯 `src/statemachine_engine/ui/public/modules/MachineStateManager.js`
```javascript
// TODO: Extend for batch instance tracking
// - groupInstancesByType() - group machines by FSM type
// - getInstancesInState() - filter instances by current state
// - calculateBatchProgress() - aggregate progress metrics
// - detectBatchStates() - identify states with multiple instances
```

## KanbanManager.js Architecture

### Class Structure
```javascript
export class KanbanManager {
    constructor(container, logger) {
        this.container = container;           // Kanban modal container
        this.logger = logger;                 // Shared logger
        this.isVisible = false;               // Modal visibility state
        this.currentFsmType = null;           // Currently viewed FSM type
        this.instances = [];                  // Current instance data
        this.stateColumns = [];               // FSM state definitions
    }
    
    // Public API
    detectBatchStates(machines)              // → {fsmType: count} map
    showKanbanModal(fsmType, instances)      // Display Kanban for FSM type
    updateInstance(machineName, newState)    // Move card between columns
    closeKanbanModal()                       // Hide modal
    
    // Private methods
    _renderBoard()                           // Build column structure
    _createCard(instance)                    // Generate instance card HTML
    _animateCardMovement(card, targetColumn) // CSS transition animation
    _bindEvents()                            // Click handlers
}
```

### Integration Points
- **MachineStateManager** provides instance data
- **WebSocket events** trigger `updateInstance()` calls
- **Modal overlay** reuses existing CSS patterns
- **Keyboard shortcuts** for quick access (K key)

## Success Criteria

1. **Demo Ready:** Patient records FSM with 10 concurrent instances
2. **UI Enhanced:** Keyboard shortcut (K) opens Kanban view for batch FSMs
3. **Zero Breakage:** Existing single-FSM view unchanged
4. **Real-time:** Cards animate between columns on state changes
5. **Minimal Code:** <150 lines KanbanManager.js, <100 lines CSS, <50 lines integration

## Technical Notes

- **No database changes** - use existing machine_states table
- **No engine changes** - leverage current multi-instance support  
- **No websocket changes** - use existing state_change events
- **CSS-first approach** - minimize JavaScript complexity
- **Progressive enhancement** - Kanban view optional, FSM diagram remains primary
- **Modular design** - KanbanManager.js as separate module keeps DiagramManager.js clean

## Detailed Implementation Spec

### KanbanManager.js Module (~150 lines)
```javascript
export class KanbanManager {
    // Constructor: Setup modal container and event bindings
    // detectBatchStates(): Group machines by FSM type, return {type: count}
    // showKanbanModal(): Extract states from first machine, create columns
    // updateInstance(): Find card by machine name, animate to new column
    // _renderBoard(): CSS Grid layout with drag-drop zones
    // _createCard(): Instance ID, current state, progress indicator
    // _animateCardMovement(): CSS transitions for smooth movement
}
```

### Integration Points
1. **app-modular.js**: Import KanbanManager, bind to 'K' key
2. **MachineStateManager**: Add `getInstancesByType()` method
3. **index.html**: Add `#kanban-modal` with CSS Grid structure
4. **style.css**: Modal overlay, column layout, card styling

### Data Flow
```
WebSocket → app-modular.js → kanbanManager.updateInstance()
                          ↓
MachineStateManager → getInstancesByType() → KanbanManager.showKanbanModal()
```

This approach maximizes value while minimizing risk and development effort.