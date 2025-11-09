# Status Update: Machine-Card Real-Time Updates Fix

**Date:** 2025-11-09  
**Version:** v1.0.70  
**Commits:** 348a230, 9ef6d07

## Problem Summary

Machine-cards (top-level UI items showing registered FSM instances) were not being created or removed automatically when `machine_registered` and `machine_terminated` events arrived via WebSocket. The cards would only appear/update on manual page refresh.

### User Report
> "issue: machine-cards, top level items are not created / refreshed automatically"  
> "cards would be updated normally in manual refresh"

## Root Cause Analysis

### Log Analysis
From `logs/localhost-1762593393455.log`:
- ✅ WebSocket events were received correctly
- ✅ `MachineStateManager.machines` Map was being updated
- ❌ `renderMachines()` was never called to update the DOM

### Code Investigation

**In `app-modular.js` event handlers:**

1. **`machine_registered` handler (line 271-329):**
   ```javascript
   // Add to machine manager
   this.machineManager.machines.set(machine_name, {...});
   
   // Rebuild diagram tabs to include new machine
   const allMachines = Array.from(this.machineManager.machines.values());
   this.createDiagramTabs(allMachines);
   // ❌ MISSING: this.machineManager.renderMachines();
   ```

2. **`machine_terminated` handler (line 336-365):**
   ```javascript
   // Remove from machine manager
   this.machineManager.machines.delete(machine_name);
   
   // Rebuild diagram tabs to remove terminated machine
   const allMachines = Array.from(this.machineManager.machines.values());
   this.createDiagramTabs(allMachines);
   // ❌ MISSING: this.machineManager.renderMachines();
   ```

**Contrast with `MachineStateManager.handleStateChange()` (line 108-127):**
```javascript
if (!machine) {
    machine = {...};
    this.machines.set(machineName, machine);
    this.renderMachines(); // ✅ Correctly renders on new machine
    this.logger.log('info', `New machine detected: ${machineName}`);
}
```

## Solution Implemented

### Changes to `app-modular.js`

**1. Fix `machine_registered` handler (commit 348a230):**
```javascript
// Add to machine manager
this.machineManager.machines.set(machine_name, {
    machine_name,
    config_type,
    current_state,
    last_activity: data.payload?.timestamp || Date.now() / 1000  // Added timestamp
});

// Render the machine card in the UI
this.machineManager.renderMachines();  // ✅ ADDED
console.log(`[App] Created machine card for: ${machine_name}`);

// Rebuild diagram tabs to include new machine
const allMachines = Array.from(this.machineManager.machines.values());
this.createDiagramTabs(allMachines);
```

**2. Fix `machine_terminated` handler (commit 348a230):**
```javascript
// Remove from machine manager
this.machineManager.machines.delete(machine_name);

// Render machines to remove the card from UI
this.machineManager.renderMachines();  // ✅ ADDED
console.log(`[App] Removed machine card for: ${machine_name}`);

// Rebuild diagram tabs to remove terminated machine
const allMachines = Array.from(this.machineManager.machines.values());
this.createDiagramTabs(allMachines);
```

## Testing

### Expected Behavior (Now Working)
1. Start demo: `cd examples/patient_records && MACHINE_COUNT=3 ./run-demo.sh start`
2. Open UI: `http://localhost:3000`
3. Machine-cards appear automatically as workers spawn:
   - `concurrent_controller` (immediately)
   - `patient_record_job_001` (after ~0s)
   - `patient_record_job_002` (after ~5s)
   - `patient_record_job_003` (after ~10s)
4. Machine-cards disappear automatically as workers terminate
5. No manual refresh required

### Related Fix (v1.0.70)
This release also includes the previous fix for kanban card updates (commit 468b473), which addressed a similar issue where spawned FSM cards in the kanban view weren't updating in real-time.

## Release Information

**Version:** 1.0.70  
**Release Date:** 2025-11-08  
**Tag:** v1.0.70  
**Release Type:** Bug fix (patch)

### Files Modified
- `src/statemachine_engine/ui/public/app-modular.js`
- `pyproject.toml` (version bump)
- `CHANGELOG.md` (release notes)

### Release Process
1. ✅ Committed fix: `348a230`
2. ✅ Updated version and changelog: `9ef6d07`
3. ✅ Tagged release: `v1.0.70`
4. ✅ Pushed to GitHub
5. ⏳ GitHub Actions: Building and publishing to PyPI

### Monitoring
- GitHub Actions: https://github.com/sheikkinen/statemachine-engine/actions
- GitHub Release: https://github.com/sheikkinen/statemachine-engine/releases/tag/v1.0.70
- PyPI: https://pypi.org/project/statemachine-engine/1.0.70/

## Architecture Notes

### UI Component Hierarchy
```
app-modular.js (Main orchestrator)
├── WebSocketManager (Event receiving)
├── MachineStateManager (Machine state tracking + card rendering)
│   ├── machines: Map<name, {machine_name, config_type, current_state, last_activity}>
│   ├── renderMachines() - Creates/updates all machine-card DOM elements
│   └── updateMachineCard() - Updates individual card state display
├── DiagramManager (FSM visualization)
├── KanbanView (Kanban board)
└── ActivityLogger (Event log)
```

### Event Flow
```
WebSocket Event → app-modular.js handler → MachineStateManager.machines.set/delete
                                       ↓
                                 renderMachines() ← CRITICAL CALL
                                       ↓
                                  DOM Updated
```

### Key Insight
The `MachineStateManager` maintains its own `machines` Map and is responsible for rendering machine-cards. Event handlers in `app-modular.js` that modify this Map MUST call `renderMachines()` to sync the UI, otherwise changes remain invisible until the next full page render.

## Lessons Learned

1. **State-UI Synchronization:** Any direct manipulation of underlying data structures requires explicit UI update calls
2. **Event Handler Completeness:** Compare similar event handlers to ensure consistent behavior patterns
3. **Log Analysis:** Console logs showed events being received and data updated, but DOM never changed—clear indicator of missing render call
4. **Manual vs Automatic Updates:** If manual refresh works but automatic doesn't, look for missing render/update calls in event handlers

## Previous Related Work

This is the second UI real-time update fix in this release:

1. **Commit 468b473 (2025-11-08):** Fixed kanban card updates for spawned FSMs
   - Problem: Kanban cards only updated for machines matching selected diagram type
   - Solution: Moved kanban update outside diagram type conditional

2. **Commit 348a230 (2025-11-08):** Fixed machine-card creation/removal
   - Problem: Machine-cards not created/removed on events
   - Solution: Added `renderMachines()` calls in event handlers

Both issues had the same root pattern: WebSocket events received, state updated, but UI render not triggered.

## Next Steps

- Monitor GitHub Actions for successful PyPI publication
- Verify installation: `pip install statemachine-engine==1.0.70`
- Test real-time updates in production deployment
- Consider adding automated UI tests for real-time update scenarios

---

**Status:** ✅ Complete and Released  
**Impact:** High - Core UI functionality now works correctly  
**Stability:** Stable - Clean architectural fix, no side effects expected
