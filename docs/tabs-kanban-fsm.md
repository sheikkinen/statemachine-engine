# Plan: Auto-Switch Kanban/Diagram Views by Machine Type

**Date:** 2025-11-09  
**Type:** Simple Navigation Change  
**Estimate:** 2-3 hours

## Goal

Remove toggle button. Show Kanban for templated machines, Diagram for unique FSMs. Switch automatically when tab clicked.

## Current vs Proposed

**Current:** Manual toggle button switches between Kanban ⟷ Diagram  
**Proposed:** Automatic - tab selection determines view

## Implementation Checklist

### 1. Add Template Metadata (30 min)
- [ ] Add `"template": true` to `examples/patient_records/config/patient-records/metadata.json`
- [ ] Add `"template": false` to `examples/patient_records/config/concurrent-controller/metadata.json`

### 2. Update app-modular.js (1 hour)
- [ ] Add helper function:
  ```javascript
  isKanbanMachine(config_type) {
      const metadata = this.diagramManager.configMetadata.get(config_type);
      return metadata?.template === true;
  }
  ```
- [ ] Remove toggle button from `index.html`
- [ ] Remove `toggleKanban()` method
- [ ] Modify `createDiagramTabs()` click handler:
  ```javascript
  // Old:
  this.diagramManager.loadDiagram(config_type);
  
  // New:
  if (this.isKanbanMachine(config_type)) {
      this.showKanban();
      this.rebuildKanbanView();
  } else {
      this.showDiagram();
      this.diagramManager.loadDiagram(config_type);
  }
  ```

### 3. Add Show/Hide Methods (15 min)
- [ ] Add to app-modular.js:
  ```javascript
  showKanban() {
      this.kanbanContainer.style.display = 'block';
      this.diagramContainer.style.display = 'none';
  }
  
  showDiagram() {
      this.diagramContainer.style.display = 'block';
      this.kanbanContainer.style.display = 'none';
  }
  ```

### 4. Test (30 min)
- [ ] Click concurrent_controller tab → See diagram
- [ ] Click patient_record_job_001 tab → See kanban
- [ ] Switch between tabs → Views switch automatically
- [ ] State changes update correct view

### 5. Cleanup (15 min)
- [ ] Remove unused `kanbanVisible` variable
- [ ] Remove toggle button CSS if any
- [ ] Test in different browsers

## Files Changed
```
examples/patient_records/config/patient-records/metadata.json  (1 line)
examples/patient_records/config/concurrent-controller/metadata.json  (1 line)
src/statemachine_engine/ui/public/index.html  (remove button)
src/statemachine_engine/ui/public/app-modular.js  (~30 lines)
```

## Success Criteria
- ✅ No toggle button
- ✅ Correct view shows for each machine type
- ✅ Tab switching works smoothly

---

**Total Time:** ~2-3 hours  
**Complexity:** Low - Just navigation logic  
**Risk:** Very low - Simple conditional rendering


# Testing

```bash
cd /Users/sheikki/Documents/src/statemachine-engine && pip install -e ".[dev]"
cd examples/patient_records && MACHINE_COUNT=3 ./run-demo.sh start
```
