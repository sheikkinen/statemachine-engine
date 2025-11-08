# Plan: UI FSM Configuration Refresh for Dynamic Worker Spawning

**Date:** November 8, 2025  
**Issue:** Dynamic worker spawning requires UI to refresh FSM configuration to display new machines  
**Context:** Controller spawns workers dynamically; UI needs to know about new FSM configs without restart

## Problem Statement

### Current Behavior
1. **Demo starts** with controller + workers defined in `start-system.sh`
2. **UI loads** initial state from `machine_state` table
3. **Controller spawns new workers** dynamically (e.g., `patient_record_job_001`)
4. **Workers register** in `machine_state` table with their `config_type`
5. **UI shows workers** in machine list BUT cannot display their diagrams
6. **Diagram 404**: `/api/diagram/patient-records/main` works for template but not worker instances

### Root Cause
- UI fetches diagram metadata from `docs/fsm-diagrams/{config_type}/metadata.json` at startup
- New worker FSMs use same config_type (`patient-records`) as template
- When worker spawns, UI sees new machine in `machine_state` but has no diagram metadata
- Clicking worker card tries to load diagram that exists but UI hasn't indexed

### Example Flow (Current)
```
1. start-system.sh generates diagrams → docs/fsm-diagrams/
2. UI loads metadata.json files → DiagramManager.availableDiagrams
3. Controller spawns patient_record_job_001
4. Worker inserts into machine_state (config_type: patient-records)
5. UI receives state_change event → creates machine card
6. User clicks card → diagram loads (shares template config)
   ❌ Problem: If template not pre-loaded, 404
```

## Architecture Analysis

### Current State Management

**Database Layer** (`machine_state` table):
```sql
CREATE TABLE machine_state (
    machine_name TEXT PRIMARY KEY,
    current_state TEXT,
    last_activity REAL,
    pid INTEGER,
    metadata TEXT,
    config_type TEXT  -- e.g., "patient-records"
);
```

**UI Data Flow:**
```
State Machine → machine_state table → WebSocket event → UI
   (engine)        (INSERT/UPDATE)      (state_change)   (update)
```

**Diagram Loading:**
```
UI Startup → /api/diagrams/list → docs/fsm-diagrams/*/metadata.json
            → DiagramManager.availableDiagrams cache

User clicks machine → fetch /api/diagram/{config_type}/main
                    → docs/fsm-diagrams/{config_type}/main.mermaid
```

### Key Files

1. **Engine** (`src/statemachine_engine/core/engine.py`):
   - `_update_machine_state()`: INSERT/UPDATE machine_state on state change
   - `_delete_machine_state()`: DELETE on shutdown
   - Emits `state_change` events via Unix socket

2. **WebSocket Server** (`src/statemachine_engine/monitoring/websocket_server.py`):
   - `get_initial_state()`: Queries machine_state for all machines
   - `websocket_endpoint()`: Sends initial state on connect
   - Broadcasts state_change events to all clients

3. **UI Server** (`src/statemachine_engine/ui/server.cjs`):
   - `/api/diagrams/list`: Scans docs/fsm-diagrams for metadata.json
   - `/api/diagram/:machine/:name`: Serves diagram files

4. **UI Client** (`src/statemachine_engine/ui/public/`):
   - `WebSocketManager.js`: Handles WebSocket connection
   - `MachineStateManager.js`: Updates machine cards from events
   - `DiagramManager.js`: Loads and renders diagrams

## Solution Options

### Option 1: Periodic Metadata Refresh (Simple)

**Approach:** UI polls `/api/diagrams/list` every N seconds to refresh available diagrams

**Implementation:**
```javascript
// DiagramManager.js
async refreshAvailableDiagrams() {
    const response = await fetch('/api/diagrams/list');
    const diagrams = await response.json();
    this.availableDiagrams = diagrams;
    console.log(`Refreshed diagrams: ${diagrams.length} configs`);
}

// In constructor or init
setInterval(() => this.refreshAvailableDiagrams(), 5000); // Every 5s
```

**Pros:**
- Simple to implement
- No server changes needed
- Works with existing API

**Cons:**
- Polling overhead (unnecessary requests)
- 5-second delay before new diagrams available
- Not event-driven

**Effort:** ~30 tokens

---

### Option 2: WebSocket Refresh Command (Event-Driven)

**Approach:** Server sends `diagram_refresh` event when new FSM detected

**Implementation:**

**A. Detect New FSM:**
```python
# engine.py - _update_machine_state()
def _update_machine_state(self, current_state: str):
    # ... existing code ...
    
    # Check if this is first time seeing this config_type
    with job_model.db._get_connection() as conn:
        existing = conn.execute(
            "SELECT COUNT(*) FROM machine_state WHERE config_type = ?",
            (self.config_name,)
        ).fetchone()[0]
        
        if existing == 0:
            # First machine of this type - notify UI to refresh
            self._emit_realtime_event('diagram_refresh', {
                'config_type': self.config_name,
                'timestamp': time.time()
            })
```

**B. Broadcast Event:**
```python
# websocket_server.py - unix_socket_listener()
async def unix_socket_listener():
    # ... existing event handling ...
    
    if event_type == 'diagram_refresh':
        # Broadcast to all connected UIs
        await broadcaster.broadcast(json.dumps(event_data))
        logger.info(f"📋 Broadcasted diagram_refresh: {event_data.get('config_type')}")
```

**C. Handle in UI:**
```javascript
// WebSocketManager.js
this.eventHandlers = {
    initial: (data) => { /* existing */ },
    state_change: (data) => { /* existing */ },
    diagram_refresh: (data) => {
        console.log(`Diagram refresh requested for: ${data.config_type}`);
        if (this.onDiagramRefresh) {
            this.onDiagramRefresh(data);
        }
    }
};

// app-modular.js
this.wsManager = new WebSocketManager({
    // ... existing handlers ...
    diagram_refresh: (data) => {
        this.logger.log('info', `Refreshing diagrams for ${data.config_type}`);
        this.diagramManager.refreshAvailableDiagrams();
        
        // Auto-create tab if this is a new config type
        const machines = this.machineManager.getMachinesByConfigType(data.config_type);
        if (machines.length > 0 && !this.diagramTabs[data.config_type]) {
            this.createDiagramTab(machines[0]);
        }
    }
});
```

**Pros:**
- Event-driven (immediate)
- No polling overhead
- Scales to many machines
- Follows existing architecture

**Cons:**
- Requires engine change
- Need to track "first of type"
- More complex

**Effort:** ~200 tokens

---

### Option 3: Client-Side Lazy Loading (On-Demand)

**Approach:** UI fetches diagram metadata when user clicks machine card (if not cached)

**Implementation:**
```javascript
// DiagramManager.js
async loadDiagram(machineName, configType, stateName) {
    // Check if we have metadata for this config
    if (!this.availableDiagrams[configType]) {
        console.log(`Fetching metadata for new config: ${configType}`);
        await this.fetchConfigMetadata(configType);
    }
    
    // Now load diagram as usual
    // ... existing code ...
}

async fetchConfigMetadata(configType) {
    try {
        const response = await fetch(`/api/diagram/${configType}/metadata`);
        if (response.ok) {
            const metadata = await response.json();
            this.availableDiagrams[configType] = metadata;
            console.log(`Loaded metadata for ${configType}`);
        }
    } catch (error) {
        console.error(`Failed to fetch metadata for ${configType}:`, error);
    }
}
```

**Server Enhancement:**
```javascript
// server.cjs - add metadata endpoint
app.get('/api/diagram/:machine/metadata', (req, res) => {
    const { machine } = req.params;
    const metadataPath = path.join(PROJECT_ROOT, 'docs', 'fsm-diagrams', machine, 'metadata.json');
    
    if (fs.existsSync(metadataPath)) {
        res.header('Access-Control-Allow-Origin', '*');
        res.json(JSON.parse(fs.readFileSync(metadataPath, 'utf8')));
    } else {
        res.status(404).json({ error: 'Metadata not found' });
    }
});
```

**Pros:**
- Lazy loading (fetch only when needed)
- No polling or events
- Works for both pre-existing and dynamic FSMs
- Minimal server changes

**Cons:**
- Slight delay on first click
- Doesn't proactively discover new configs

**Effort:** ~150 tokens

---

### Option 4: Hybrid: Event + Lazy Loading (Recommended)

**Approach:** Combine Options 2 & 3 for best of both worlds

**Flow:**
1. **Worker spawns** → Engine emits `machine_registered` event (new event type)
2. **WebSocket broadcasts** event to all UIs
3. **UI receives event** → Checks if config_type is new
4. **If new** → Lazy fetch metadata via `/api/diagram/{config_type}/metadata`
5. **If exists** → Use cached metadata
6. **User clicks** → Diagram loads immediately (metadata already cached)

**Implementation:**

**A. Engine Event:**
```python
# engine.py - _update_machine_state()
def _update_machine_state(self, current_state: str):
    # ... existing INSERT/UPDATE ...
    
    # Emit machine_registered event (every time, let UI decide if new)
    self._emit_realtime_event('machine_registered', {
        'machine_name': self.machine_name,
        'config_type': self.config_name,
        'current_state': current_state,
        'timestamp': time.time()
    })
```

**B. WebSocket Broadcast:**
```python
# websocket_server.py - unix_socket_listener()
# No changes needed - already broadcasts all events
```

**C. UI Handler:**
```javascript
// WebSocketManager.js - add handler
this.eventHandlers = {
    // ... existing ...
    machine_registered: (data) => {
        if (this.onMachineRegistered) {
            this.onMachineRegistered(data);
        }
    }
};

// app-modular.js
this.wsManager = new WebSocketManager({
    // ... existing ...
    machine_registered: async (data) => {
        this.logger.log('info', `Machine registered: ${data.machine_name} (${data.config_type})`);
        
        // Check if we have metadata for this config
        if (!this.diagramManager.hasConfig(data.config_type)) {
            this.logger.log('info', `New config detected: ${data.config_type}, fetching metadata...`);
            await this.diagramManager.fetchConfigMetadata(data.config_type);
            
            // Create diagram tab if this is first machine of this type
            if (!this.diagramTabs[data.config_type]) {
                await this.createDiagramTabForConfig(data.config_type, data.machine_name);
            }
        }
    }
});
```

**D. DiagramManager Enhancement:**
```javascript
// DiagramManager.js
hasConfig(configType) {
    return !!this.availableDiagrams[configType];
}

async fetchConfigMetadata(configType) {
    try {
        const response = await fetch(`/api/diagram/${configType}/metadata`);
        if (response.ok) {
            const metadata = await response.json();
            this.availableDiagrams[configType] = metadata;
            this.logger.log('info', `Loaded metadata for ${configType}: ${metadata.diagrams.length} diagrams`);
            return true;
        }
    } catch (error) {
        this.logger.log('error', `Failed to fetch metadata for ${configType}: ${error.message}`);
        return false;
    }
}
```

**E. Server Endpoint:**
```javascript
// server.cjs - add metadata endpoint (same as Option 3)
app.get('/api/diagram/:machine/metadata', (req, res) => {
    const { machine } = req.params;
    const metadataPath = path.join(PROJECT_ROOT, 'docs', 'fsm-diagrams', machine, 'metadata.json');
    
    if (fs.existsSync(metadataPath)) {
        res.header('Access-Control-Allow-Origin', '*');
        res.json(JSON.parse(fs.readFileSync(metadataPath, 'utf8')));
    } else {
        res.status(404).json({ error: 'Metadata not found' });
    }
});
```

**Pros:**
- ✅ Event-driven (immediate notification)
- ✅ Lazy loading (fetch only when new)
- ✅ Scales well (no polling)
- ✅ Works for startup and runtime
- ✅ Minimal overhead (only new configs fetched)

**Cons:**
- Requires engine + server + UI changes
- More code than simpler options

**Effort:** ~300 tokens

---

## Recommendation: **Option 4 (Hybrid)**

### Rationale
1. **Best UX**: Immediate response when worker spawns
2. **Efficient**: No polling, fetch only when needed
3. **Scalable**: Works for 1 or 100 workers
4. **Consistent**: Follows existing event architecture
5. **Robust**: Handles edge cases (config exists but not loaded)

### Implementation Plan

#### Phase 1: Engine Event Emission
**File:** `src/statemachine_engine/core/engine.py`
- Modify `_update_machine_state()` to emit `machine_registered` event
- Include: machine_name, config_type, current_state, timestamp

#### Phase 2: Server Metadata Endpoint
**File:** `src/statemachine_engine/ui/server.cjs`
- Add `/api/diagram/:machine/metadata` endpoint
- Return metadata.json for specified config_type

#### Phase 3: UI Event Handling
**Files:** 
- `src/statemachine_engine/ui/public/modules/WebSocketManager.js`
- `src/statemachine_engine/ui/public/app-modular.js`
- `src/statemachine_engine/ui/public/modules/DiagramManager.js`

**Changes:**
- Add `machine_registered` event handler
- Implement `fetchConfigMetadata()` in DiagramManager
- Auto-create diagram tab for new config types

#### Phase 4: Testing
1. Start demo with controller only (no workers)
2. Controller spawns worker → verify `machine_registered` event
3. UI fetches metadata → verify `/api/diagram/patient-records/metadata` call
4. Click worker card → verify diagram loads immediately
5. Spawn 10 workers → verify only 1 metadata fetch (first worker)

### Alternative: Quick Fix (Option 3 Only)

If immediate implementation not feasible, implement **Option 3 (Lazy Loading)** as quick fix:
- Add metadata endpoint (5 min)
- Modify DiagramManager.loadDiagram() to lazy fetch (10 min)
- **Total effort:** ~15 minutes, ~150 tokens

This solves the immediate problem but doesn't provide proactive UI updates.

---

## Additional Considerations

### Diagram Generation Timing
Currently diagrams generated at startup by `start-system.sh`. For dynamic workers:

**Option A:** Generate diagrams on-demand (worker startup)
- Engine generates diagram when config first loaded
- Requires diagram generation in Python

**Option B:** Pre-generate all templates at startup
- Current approach - works for shared config_type
- No changes needed

**Recommendation:** Keep Option B (current approach). Workers share template diagrams, only metadata needs refreshing.

### Config Type Naming
Workers use parent config's name (e.g., `patient-records` for all patient record workers). This is correct - they share diagram templates. UI should:
- Display config_type in machine card
- Group machines by config_type in Kanban view
- Share diagram tabs across instances (already implemented)

### Machine State Cleanup
When worker terminates:
- Engine calls `_delete_machine_state()`
- UI receives implicit removal (no state_change events)
- UI should handle stale machines (cleanup after N seconds of inactivity)

**Enhancement:** Add `machine_terminated` event:
```python
# engine.py - _delete_machine_state()
def _delete_machine_state(self):
    # ... existing DELETE ...
    self._emit_realtime_event('machine_terminated', {
        'machine_name': self.machine_name,
        'config_type': self.config_name,
        'timestamp': time.time()
    })
```

UI can then immediately remove card instead of waiting for timeout.

---

## Summary

**Issue:** UI cannot display diagrams for dynamically spawned workers  
**Root Cause:** Diagram metadata not loaded for new config types  
**Solution:** Hybrid approach with event-driven metadata refresh + lazy loading  
**Implementation:** 3 phases (engine event, server endpoint, UI handling)  
**Effort:** ~300 tokens for full solution, ~150 for quick fix  
**Timeline:** 1-2 hours for full implementation

**Files to Modify:**
1. `src/statemachine_engine/core/engine.py` (+20 lines)
2. `src/statemachine_engine/ui/server.cjs` (+15 lines)
3. `src/statemachine_engine/ui/public/modules/WebSocketManager.js` (+10 lines)
4. `src/statemachine_engine/ui/public/app-modular.js` (+25 lines)
5. `src/statemachine_engine/ui/public/modules/DiagramManager.js` (+30 lines)

**Testing:** Verify with patient_records demo (controller + dynamic workers)
