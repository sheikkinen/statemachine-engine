# Plan: CSS-Only Updates (Bare Bones - Dev Only)

**Document Type:** Bare Bones Implementation Plan
**Created:** 2025-10-26
**Target:** Dev installation only (no production concerns)
**Estimated Effort:** 4-6 hours (single session)

## Core Concept

**Metadata-Driven CSS Updates**

1. After Mermaid renders: Build state→target lookup map from metadata
2. Enrich SVG: Add data attributes to elements
3. On state change: Lookup target → Query by data attribute → Toggle CSS class
4. Performance: ~150ms first render, ~1ms subsequent updates

**Key Innovation:** Metadata tells us WHAT to highlight (composite vs state), SVG enrichment makes it FAST

## Flow Diagram

```
Backend Event: "monitoring_sdxl"
    ↓
┌─────────────────────────────────────────┐
│ renderDiagram('monitoring_sdxl')        │
└─────────────────────────────────────────┘
    ↓
    ├──→ Fast Path Check
    │    ↓
    │    stateHighlightMap exists? ──→ NO ──→ [SLOW PATH]
    │    ↓ YES
    │    Lookup: stateHighlightMap['monitoring_sdxl']
    │    ↓
    │    Returns: {type:'composite', target:'SDXLLIFECYCLE', class:'activeComposite'}
    │    ↓
    │    querySelector('[data-state-id="SDXLLIFECYCLE"]')
    │    ↓
    │    Found? ──→ NO ──→ [SLOW PATH]
    │    ↓ YES
    │    node.classList.add('activeComposite')
    │    ↓
    │    ✅ DONE (~1ms)
    │
    └──→ Slow Path (Full Render)
         ↓
         Mermaid.run() (~100ms)
         ↓
         buildStateHighlightMap() (<5ms)
         ├─ Main diagram: Map states → composites
         └─ Subdiagram: Map states → states
         ↓
         enrichSvgWithDataAttributes() (<10ms)
         └─ Add data-state-id to all targets
         ↓
         ✅ DONE + Ready for fast path (~120ms)

Main Diagram Map Example:
{
  "monitoring_sdxl": {type: "composite", target: "SDXLLIFECYCLE", class: "activeComposite"},
  "completing_sdxl": {type: "composite", target: "SDXLLIFECYCLE", class: "activeComposite"},
  "checking_queue": {type: "composite", target: "QUEUEMANAGEMENT", class: "activeComposite"}
}

Subdiagram Map Example:
{
  "monitoring_sdxl": {type: "state", target: "monitoring_sdxl", class: "active"},
  "completing_sdxl": {type: "state", target: "completing_sdxl", class: "active"}
}
```

## Implementation Steps

### DiagramManager ([src/statemachine_engine/ui/static/js/DiagramManager.js](../src/statemachine_engine/ui/static/js/DiagramManager.js))

#### Step 1: Build State Highlight Lookup Map (30 min)

**Action:** Add `buildStateHighlightMap()` - pre-compute what to highlight for each state

```javascript
buildStateHighlightMap() {
    const map = {};

    if (!this.diagramMetadata?.diagrams) {
        console.warn('[Map] No metadata - will fallback to full render');
        return null;
    }

    const currentDiagram = this.diagramMetadata.diagrams[this.currentDiagramName];
    if (!currentDiagram) return null;

    // Main diagram: Map states → composites
    if (this.currentDiagramName === 'main') {
        for (const [compositeName, compositeData] of Object.entries(this.diagramMetadata.diagrams)) {
            if (compositeName === 'main') continue;

            if (compositeData.states && Array.isArray(compositeData.states)) {
                for (const stateName of compositeData.states) {
                    map[stateName] = {
                        type: 'composite',
                        target: compositeName,
                        class: 'activeComposite'
                    };
                }
            }
        }
        console.log(`[Map] Main diagram: ${Object.keys(map).length} states → composites`);
    }
    // Subdiagram: Direct state mapping
    else {
        if (currentDiagram.states && Array.isArray(currentDiagram.states)) {
            for (const stateName of currentDiagram.states) {
                map[stateName] = {
                    type: 'state',
                    target: stateName,
                    class: 'active'
                };
            }
            console.log(`[Map] ${this.currentDiagramName}: ${Object.keys(map).length} states`);
        }
    }

    return map;
}
```

**Where:** New method in DiagramManager class

#### Step 2: Add SVG Enrichment Method (30 min)

**Action:** Add `enrichSvgWithDataAttributes()` - add data-state-id to all targets

```javascript
enrichSvgWithDataAttributes() {
    const svg = this.container.querySelector('svg');
    if (!svg || !this.stateHighlightMap) return false;

    let enrichedCount = 0;
    const targets = new Set(Object.values(this.stateHighlightMap).map(e => e.target));

    // Enrich state nodes
    const stateNodes = svg.querySelectorAll('g.node');
    stateNodes.forEach(node => {
        const textEl = node.querySelector('text');
        const stateName = textEl ? textEl.textContent.trim() : '';

        if (stateName && targets.has(stateName)) {
            node.dataset.stateId = stateName;
            enrichedCount++;
        }
    });

    // Enrich edge paths
    const edgeLabels = svg.querySelectorAll('g.edgeLabels g.label');
    edgeLabels.forEach(label => {
        const eventName = label.textContent.trim();
        const dataId = label.dataset.id;
        if (eventName && dataId) {
            const path = svg.querySelector(`path[data-id="${dataId}"]`);
            if (path) {
                path.dataset.edgeEvent = eventName;
                enrichedCount++;
            }
        }
    });

    console.log(`[Enrich] ✓ ${enrichedCount} elements enriched`);
    return enrichedCount > 0;
}
```

**Where:** New method in DiagramManager class

#### Step 3: Add CSS-Only Update Method (30 min)

**Action:** Add `updateStateHighlight()` - lookup state → find target → highlight

```javascript
updateStateHighlight(stateName, eventName = null) {
    const svg = this.container.querySelector('svg');
    if (!svg) return false;

    // Check if we have the map
    if (!this.stateHighlightMap) {
        console.warn('[CSS-only] No state map - fallback');
        return false;
    }

    // Lookup what to highlight
    const entry = this.stateHighlightMap[stateName];
    if (!entry) {
        console.warn(`[CSS-only] State "${stateName}" not in map - fallback`);
        return false;
    }

    // Remove old highlights
    svg.querySelectorAll('.active, .activeComposite').forEach(el => {
        el.classList.remove('active', 'activeComposite');
    });

    // Find target node
    const node = svg.querySelector(`[data-state-id="${entry.target}"]`);
    if (!node) {
        console.warn(`[CSS-only] Node not found for "${entry.target}" - fallback`);
        return false;
    }

    // Apply highlighting
    node.classList.add(entry.class);

    if (entry.type === 'composite') {
        console.log(`[CSS-only] ✓ Composite: ${entry.target} (~1ms)`);
    } else {
        console.log(`[CSS-only] ✓ State: ${entry.target} (~1ms)`);
    }

    // Highlight arrow
    if (eventName) {
        svg.querySelectorAll('.last-transition-arrow').forEach(el => {
            el.classList.remove('last-transition-arrow');
        });

        const edge = svg.querySelector(`[data-edge-event="${eventName}"]`);
        if (edge) {
            edge.classList.add('last-transition-arrow');
            setTimeout(() => edge.classList.remove('last-transition-arrow'), 2000);
        }
    }

    return true;
}
```

**Where:** New method in DiagramManager class

#### Step 4: Wire Fast Path into renderDiagram() (30 min)

**Action:** Try fast path → fallback to slow path if needed

```javascript
async renderDiagram(highlightState = null, transition = null) {
    // Attempt fast path (CSS-only)
    if (highlightState) {
        const success = this.updateStateHighlight(highlightState, transition?.event);
        if (success) {
            console.log('[Render] ✓ Fast path (~1ms)');
            return;
        }
        console.log('[Render] Fast path failed, using slow path');
    }

    // Slow path: Full Mermaid render
    if (!this.currentDiagram) return;

    try {
        let diagramCode = this.currentDiagram;

        // ... existing highlighting logic (v1.0.30 approach) ...
        // findCompositeForState(), add CSS classes, etc.

        // Render with Mermaid
        this.container.classList.add('redrawing');
        await new Promise(resolve => setTimeout(resolve, 50));

        this.container.innerHTML = `<pre class="mermaid">${diagramCode}</pre>`;
        const mermaidEl = this.container.querySelector('.mermaid');
        await window.mermaid.run({ nodes: [mermaidEl] });

        this.container.classList.remove('redrawing');
        this.container.classList.add('has-diagram');

        // Build map for next fast path
        this.stateHighlightMap = this.buildStateHighlightMap();

        if (this.stateHighlightMap) {
            const enriched = this.enrichSvgWithDataAttributes();
            if (enriched) {
                this.container.dataset.enriched = 'true';
                console.log('[Render] ✓ Ready for fast path');
            } else {
                this.container.dataset.enriched = 'false';
            }
        } else {
            this.container.dataset.enriched = 'false';
        }

        this.attachCompositeClickHandlers();

        console.log('[Render] ✓ Full render (~150ms)');

    } catch (error) {
        console.error('[Render] Error:', error);
        this.container.dataset.enriched = 'false';
    }
}
```

**Where:** Replace existing `renderDiagram()` method

#### Step 5: Clear State on Diagram Load (5 min)

**Action:** Reset enrichment and map when switching diagrams

```javascript
async loadDiagram(machineName, diagramName = 'main') {
    // Clear fast path state
    this.container.dataset.enriched = 'false';
    this.stateHighlightMap = null;

    // ... existing load logic ...
}
```

**Where:** Beginning of `loadDiagram()` method

## File Changes Summary

### Modified Files

**src/statemachine_engine/ui/static/js/DiagramManager.js**
- Add method: `buildStateHighlightMap()` (~40 lines) - NEW: Metadata-driven lookup table
- Add method: `enrichSvgWithDataAttributes()` (~35 lines) - Uses map to enrich only targets
- Add method: `updateStateHighlight()` (~35 lines) - Lookup-based highlighting with fallback
- Modify method: `renderDiagram()` (~45 lines changed) - Fast path attempt + map building
- Modify method: `loadDiagram()` (~2 lines added) - Clear map and enrichment

**Total additions:** ~110 lines of code (was ~55 without composite support)

## Testing Steps

### Unit Tests (1-2 hours)

Create test file: `src/statemachine_engine/ui/static/js/tests/DiagramManager.test.js`

#### Test 1: buildStateHighlightMap() - Main Diagram

```javascript
describe('buildStateHighlightMap', () => {
    let diagramManager;

    beforeEach(() => {
        diagramManager = new DiagramManager();
        diagramManager.container = document.createElement('div');
    });

    it('should build map for main diagram with composites', () => {
        // Setup
        diagramManager.diagramMetadata = {
            diagrams: {
                main: { composites: ['SDXLLIFECYCLE', 'QUEUEMANAGEMENT'] },
                SDXLLIFECYCLE: { states: ['monitoring_sdxl', 'completing_sdxl'] },
                QUEUEMANAGEMENT: { states: ['checking_queue', 'dispatching'] }
            }
        };
        diagramManager.currentDiagramName = 'main';

        // Execute
        const map = diagramManager.buildStateHighlightMap();

        // Verify
        expect(map).not.toBeNull();
        expect(Object.keys(map).length).toBe(4);

        expect(map['monitoring_sdxl']).toEqual({
            type: 'composite',
            target: 'SDXLLIFECYCLE',
            class: 'activeComposite'
        });

        expect(map['checking_queue']).toEqual({
            type: 'composite',
            target: 'QUEUEMANAGEMENT',
            class: 'activeComposite'
        });
    });

    it('should build map for subdiagram with direct states', () => {
        // Setup
        diagramManager.diagramMetadata = {
            diagrams: {
                main: { composites: ['SDXLLIFECYCLE'] },
                SDXLLIFECYCLE: { states: ['monitoring_sdxl', 'completing_sdxl'] }
            }
        };
        diagramManager.currentDiagramName = 'SDXLLIFECYCLE';

        // Execute
        const map = diagramManager.buildStateHighlightMap();

        // Verify
        expect(map).not.toBeNull();
        expect(Object.keys(map).length).toBe(2);

        expect(map['monitoring_sdxl']).toEqual({
            type: 'state',
            target: 'monitoring_sdxl',
            class: 'active'
        });
    });

    it('should return null when metadata missing', () => {
        diagramManager.diagramMetadata = null;
        diagramManager.currentDiagramName = 'main';

        const map = diagramManager.buildStateHighlightMap();

        expect(map).toBeNull();
    });

    it('should return null when current diagram not in metadata', () => {
        diagramManager.diagramMetadata = {
            diagrams: { main: {} }
        };
        diagramManager.currentDiagramName = 'NONEXISTENT';

        const map = diagramManager.buildStateHighlightMap();

        expect(map).toBeNull();
    });
});
```

#### Test 2: enrichSvgWithDataAttributes()

```javascript
describe('enrichSvgWithDataAttributes', () => {
    let diagramManager;

    beforeEach(() => {
        diagramManager = new DiagramManager();
        diagramManager.container = document.createElement('div');

        // Create mock SVG structure
        diagramManager.container.innerHTML = `
            <svg>
                <g class="node" id="flowchart-SDXLLIFECYCLE-123">
                    <rect></rect>
                    <text>SDXLLIFECYCLE</text>
                </g>
                <g class="node" id="flowchart-QUEUEMANAGEMENT-456">
                    <rect></rect>
                    <text>QUEUEMANAGEMENT</text>
                </g>
                <g class="edgeLabels">
                    <g class="label" data-id="L-start-processing-0">
                        <text>new_job</text>
                    </g>
                </g>
                <path data-id="L-start-processing-0" class="edge"></path>
            </svg>
        `;
    });

    it('should enrich state nodes with data-state-id', () => {
        // Setup map
        diagramManager.stateHighlightMap = {
            'monitoring_sdxl': { type: 'composite', target: 'SDXLLIFECYCLE', class: 'activeComposite' },
            'checking_queue': { type: 'composite', target: 'QUEUEMANAGEMENT', class: 'activeComposite' }
        };

        // Execute
        const result = diagramManager.enrichSvgWithDataAttributes();

        // Verify
        expect(result).toBe(true);

        const svg = diagramManager.container.querySelector('svg');
        const sdxlNode = svg.querySelector('g.node:nth-child(1)');
        const queueNode = svg.querySelector('g.node:nth-child(2)');

        expect(sdxlNode.dataset.stateId).toBe('SDXLLIFECYCLE');
        expect(queueNode.dataset.stateId).toBe('QUEUEMANAGEMENT');
    });

    it('should enrich edge paths with data-edge-event', () => {
        diagramManager.stateHighlightMap = {};

        // Execute
        diagramManager.enrichSvgWithDataAttributes();

        // Verify
        const svg = diagramManager.container.querySelector('svg');
        const edge = svg.querySelector('path[data-id="L-start-processing-0"]');

        expect(edge.dataset.edgeEvent).toBe('new_job');
    });

    it('should return false when no SVG', () => {
        diagramManager.container.innerHTML = '';
        diagramManager.stateHighlightMap = {};

        const result = diagramManager.enrichSvgWithDataAttributes();

        expect(result).toBe(false);
    });

    it('should return false when no stateHighlightMap', () => {
        diagramManager.stateHighlightMap = null;

        const result = diagramManager.enrichSvgWithDataAttributes();

        expect(result).toBe(false);
    });

    it('should only enrich nodes that are in the map', () => {
        // Map only includes SDXLLIFECYCLE
        diagramManager.stateHighlightMap = {
            'monitoring_sdxl': { type: 'composite', target: 'SDXLLIFECYCLE', class: 'activeComposite' }
        };

        // Execute
        diagramManager.enrichSvgWithDataAttributes();

        // Verify
        const svg = diagramManager.container.querySelector('svg');
        const sdxlNode = svg.querySelector('g.node:nth-child(1)');
        const queueNode = svg.querySelector('g.node:nth-child(2)');

        expect(sdxlNode.dataset.stateId).toBe('SDXLLIFECYCLE');
        expect(queueNode.dataset.stateId).toBeUndefined(); // Not in map
    });
});
```

#### Test 3: updateStateHighlight()

```javascript
describe('updateStateHighlight', () => {
    let diagramManager;

    beforeEach(() => {
        diagramManager = new DiagramManager();
        diagramManager.container = document.createElement('div');

        // Create enriched SVG
        diagramManager.container.innerHTML = `
            <svg>
                <g class="node" data-state-id="SDXLLIFECYCLE">
                    <rect></rect>
                    <text>SDXLLIFECYCLE</text>
                </g>
                <g class="node" data-state-id="QUEUEMANAGEMENT">
                    <rect></rect>
                    <text>QUEUEMANAGEMENT</text>
                </g>
                <path data-edge-event="sdxl_job_done" class="edge"></path>
            </svg>
        `;

        // Setup map
        diagramManager.stateHighlightMap = {
            'monitoring_sdxl': {
                type: 'composite',
                target: 'SDXLLIFECYCLE',
                class: 'activeComposite'
            },
            'checking_queue': {
                type: 'composite',
                target: 'QUEUEMANAGEMENT',
                class: 'activeComposite'
            }
        };
    });

    it('should highlight composite node for state in map', () => {
        const result = diagramManager.updateStateHighlight('monitoring_sdxl');

        expect(result).toBe(true);

        const svg = diagramManager.container.querySelector('svg');
        const node = svg.querySelector('[data-state-id="SDXLLIFECYCLE"]');

        expect(node.classList.contains('activeComposite')).toBe(true);
    });

    it('should remove old highlights before adding new', () => {
        // First highlight
        diagramManager.updateStateHighlight('monitoring_sdxl');

        const svg = diagramManager.container.querySelector('svg');
        const sdxlNode = svg.querySelector('[data-state-id="SDXLLIFECYCLE"]');
        expect(sdxlNode.classList.contains('activeComposite')).toBe(true);

        // Second highlight
        diagramManager.updateStateHighlight('checking_queue');

        // Old highlight removed
        expect(sdxlNode.classList.contains('activeComposite')).toBe(false);

        // New highlight added
        const queueNode = svg.querySelector('[data-state-id="QUEUEMANAGEMENT"]');
        expect(queueNode.classList.contains('activeComposite')).toBe(true);
    });

    it('should highlight transition arrow when event provided', () => {
        jest.useFakeTimers();

        const result = diagramManager.updateStateHighlight('monitoring_sdxl', 'sdxl_job_done');

        expect(result).toBe(true);

        const svg = diagramManager.container.querySelector('svg');
        const edge = svg.querySelector('[data-edge-event="sdxl_job_done"]');

        expect(edge.classList.contains('last-transition-arrow')).toBe(true);

        // Arrow should be cleared after 2 seconds
        jest.advanceTimersByTime(2000);
        expect(edge.classList.contains('last-transition-arrow')).toBe(false);

        jest.useRealTimers();
    });

    it('should return false when state not in map', () => {
        const result = diagramManager.updateStateHighlight('unknown_state');

        expect(result).toBe(false);
    });

    it('should return false when node not found in SVG', () => {
        // Add state to map but node not in SVG
        diagramManager.stateHighlightMap['new_state'] = {
            type: 'composite',
            target: 'NONEXISTENT',
            class: 'activeComposite'
        };

        const result = diagramManager.updateStateHighlight('new_state');

        expect(result).toBe(false);
    });

    it('should return false when no SVG', () => {
        diagramManager.container.innerHTML = '';

        const result = diagramManager.updateStateHighlight('monitoring_sdxl');

        expect(result).toBe(false);
    });

    it('should return false when no stateHighlightMap', () => {
        diagramManager.stateHighlightMap = null;

        const result = diagramManager.updateStateHighlight('monitoring_sdxl');

        expect(result).toBe(false);
    });
});
```

#### Test 4: Integration - Fast Path vs Slow Path

```javascript
describe('renderDiagram - Fast vs Slow Path', () => {
    let diagramManager;

    beforeEach(() => {
        diagramManager = new DiagramManager();
        diagramManager.container = document.createElement('div');
        diagramManager.currentDiagram = 'flowchart TD\n  A-->B';

        // Mock methods
        diagramManager.updateStateHighlight = jest.fn();
        diagramManager.fullMermaidRender = jest.fn();
    });

    it('should use fast path when enriched and state provided', async () => {
        diagramManager.container.dataset.enriched = 'true';
        diagramManager.stateHighlightMap = { 'test': {} };
        diagramManager.updateStateHighlight.mockReturnValue(true);

        await diagramManager.renderDiagram('test_state', { event: 'test_event' });

        expect(diagramManager.updateStateHighlight).toHaveBeenCalledWith('test_state', 'test_event');
        expect(diagramManager.fullMermaidRender).not.toHaveBeenCalled();
    });

    it('should use slow path when updateStateHighlight returns false', async () => {
        diagramManager.container.dataset.enriched = 'true';
        diagramManager.stateHighlightMap = { 'test': {} };
        diagramManager.updateStateHighlight.mockReturnValue(false);

        await diagramManager.renderDiagram('test_state');

        expect(diagramManager.updateStateHighlight).toHaveBeenCalled();
        expect(diagramManager.fullMermaidRender).toHaveBeenCalled();
    });

    it('should use slow path when no highlight state', async () => {
        diagramManager.container.dataset.enriched = 'true';

        await diagramManager.renderDiagram(null);

        expect(diagramManager.updateStateHighlight).not.toHaveBeenCalled();
        expect(diagramManager.fullMermaidRender).toHaveBeenCalled();
    });
});
```

#### Test 5: Diagram Switching

```javascript
describe('loadDiagram - State Clearing', () => {
    let diagramManager;

    beforeEach(() => {
        diagramManager = new DiagramManager();
        diagramManager.container = document.createElement('div');

        // Mock fetch
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({
                    mermaid_code: 'flowchart TD\n  A-->B',
                    metadata: { diagrams: { main: {} } }
                })
            })
        );

        // Mock other methods
        diagramManager.updateBreadcrumb = jest.fn();
        diagramManager.loadMachineState = jest.fn(() => null);
        diagramManager.loadMachineTransition = jest.fn(() => null);
        diagramManager.fullMermaidRender = jest.fn();
    });

    it('should clear enrichment flag and map on diagram load', async () => {
        // Setup existing state
        diagramManager.container.dataset.enriched = 'true';
        diagramManager.stateHighlightMap = { 'old': {} };

        await diagramManager.loadDiagram('test-machine', 'main');

        expect(diagramManager.container.dataset.enriched).toBe('false');
        expect(diagramManager.stateHighlightMap).toBeNull();
    });
});
```

### Running Unit Tests

```bash
# Install test dependencies
npm install --save-dev jest @testing-library/dom

# Add to package.json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch"
  }
}

# Run tests
npm test

# Expected output:
# PASS  src/statemachine_engine/ui/static/js/tests/DiagramManager.test.js
#   buildStateHighlightMap
#     ✓ should build map for main diagram with composites (3ms)
#     ✓ should build map for subdiagram with direct states (1ms)
#     ✓ should return null when metadata missing (1ms)
#     ✓ should return null when current diagram not in metadata (1ms)
#   enrichSvgWithDataAttributes
#     ✓ should enrich state nodes with data-state-id (2ms)
#     ✓ should enrich edge paths with data-edge-event (1ms)
#     ✓ should return false when no SVG (1ms)
#     ✓ should return false when no stateHighlightMap (1ms)
#     ✓ should only enrich nodes that are in the map (2ms)
#   updateStateHighlight
#     ✓ should highlight composite node for state in map (2ms)
#     ✓ should remove old highlights before adding new (2ms)
#     ✓ should highlight transition arrow when event provided (2ms)
#     ✓ should return false when state not in map (1ms)
#     ✓ should return false when node not found in SVG (1ms)
#     ✓ should return false when no SVG (1ms)
#     ✓ should return false when no stateHighlightMap (1ms)
#   renderDiagram - Fast vs Slow Path
#     ✓ should use fast path when enriched and state provided (1ms)
#     ✓ should use slow path when updateStateHighlight returns false (1ms)
#     ✓ should use slow path when no highlight state (1ms)
#   loadDiagram - State Clearing
#     ✓ should clear enrichment flag and map on diagram load (5ms)
#
# Test Suites: 1 passed, 1 total
# Tests:       20 passed, 20 total
```

### Manual Testing (1 hour)

1. **Initial Load**
   ```bash
   # Start UI
   statemachine-ui

   # In browser console, verify:
   document.querySelector('#diagram').dataset.enriched === 'true'
   ```

2. **Fast Path Test**
   ```bash
   # Send state change
   statemachine-cli send-event controller new_job

   # Check console logs for:
   "[CSS-only] processing (~1ms)"
   ```

3. **Rapid Updates Test**
   ```bash
   # Send 10 events quickly
   for i in {1..10}; do
       statemachine-cli send-event controller next_state
       sleep 0.5
   done

   # Verify: No flicker, all CSS-only
   ```

4. **Composite State Test (CRITICAL)**
   ```bash
   # Send state that belongs to composite
   statemachine-cli send-event controller monitoring_sdxl

   # In browser console, verify:
   # - Composite SDXLLIFECYCLE is highlighted (not individual state)
   # - Log shows: "[CSS-only] ✓ Composite: SDXLLIFECYCLE (~1ms)"
   # - Map was built: console shows state→composite mappings

   # Check map contents:
   window.diagramManager.stateHighlightMap
   # Should show: {"monitoring_sdxl": {type:"composite", target:"SDXLLIFECYCLE", class:"activeComposite"}, ...}
   ```

5. **Diagram Switching Test**
   ```
   - Load main diagram
   - Send event to highlight composite
   - Click composite state → subdiagram loads
   - Verify: Map rebuilt for subdiagram states
   - Send state change in subdiagram
   - Verify: Direct state highlighted (not composite)
   - Click breadcrumb → back to main
   - Verify: Map rebuilt for main diagram
   ```

6. **Edge Cases**
   ```
   - State not in map → fallback to full render
   - State in map but node not in SVG → fallback to full render
   - Missing metadata → fallback to full render
   - Browser refresh → full render → map rebuilds
   ```

## Success Criteria

**Must Work:**
- ✅ Composite states highlight correctly on main diagram (was broken in v1.0.33-40)
- ✅ Individual states highlight correctly on subdiagrams
- ✅ State highlight map built from metadata
- ✅ First render adds data attributes (check DevTools)
- ✅ State changes use CSS-only (<5ms, no flicker)
- ✅ Arrow highlighting works
- ✅ Diagram switching clears map and enrichment
- ✅ Automatic fallback on any failure
- ✅ No console errors

**Performance:**
- First render: ~100-120ms (acceptable)
- Map building: <5ms
- Enrichment: <10ms
- Subsequent updates: <5ms (target <2ms)
- 10 rapid updates: ~120ms total (vs ~1500ms before)

## Timeline

**Single Session (8-10 hours - with TDD approach):**
- Hour 1: Setup test environment + write unit tests for buildStateHighlightMap()
- Hour 2: Implement buildStateHighlightMap() until tests pass (Step 1)
- Hour 3: Write unit tests for enrichSvgWithDataAttributes() + implement (Step 2)
- Hour 4: Write unit tests for updateStateHighlight() + implement (Step 3)
- Hour 5: Integration tests + wire into renderDiagram() (Steps 4-5)
- Hour 6: Manual testing - composite states
- Hour 7: Manual testing - subdiagrams + diagram switching
- Hours 8-10: Edge cases, polish, documentation

**Test-First Benefits:**
- ✅ Clear requirements before coding
- ✅ Immediate feedback on correctness
- ✅ Regression safety for future changes
- ✅ Living documentation of expected behavior

## Rollback

**If issues occur:** Simple feature toggle

```javascript
// Top of renderDiagram()
const ENABLE_CSS_UPDATES = false;  // Toggle to disable
if (!ENABLE_CSS_UPDATES) {
    this.container.dataset.enriched = 'false';
    // Falls through to existing full render
}
```

## Notes

**Core Features (from replan):**
- ✅ Metadata-driven state→target lookup map
- ✅ Composite state support (main diagram)
- ✅ Direct state support (subdiagrams)
- ✅ Automatic fallback to full render
- ✅ SVG enrichment with data attributes

**Simplifications from replan:**
- ❌ No feature flags system (just simple toggle)
- ❌ No performance monitoring dashboard (console logs sufficient)
- ❌ No phased rollout (all or nothing)
- ❌ No production deployment planning (dev only)
- ❌ No extensive validation/warnings (fail → fallback)
- ❌ No A/B testing or metrics collection

**Key principle:** Metadata tells us WHAT to highlight, lookup table makes it FAST, full render is the safety net

## Comparison: Bare Bones vs Replan

| Feature | Replan (Complex) | Bare Bones (Simple) |
|---------|------------------|---------------------|
| **Composite States** | ✅ Full support | ✅ Full support |
| **Metadata Usage** | ✅ Pre-computed map | ✅ Pre-computed map |
| **Feature Flags** | ✅ 3 flags | ❌ Simple toggle |
| **Performance Monitor** | ✅ Class with stats | ❌ Console logs |
| **Validation** | ✅ Extensive warnings | ❌ Minimal (fallback) |
| **Phased Rollout** | ✅ 3 phases | ❌ All at once |
| **Timeline** | 3-4 weeks | 6-8 hours |
| **Code Lines** | ~200 lines | ~110 lines |

**What's the same:** Core algorithm (metadata map → enrichment → CSS update → fallback)
**What's different:** Production readiness features removed for dev-only implementation

---

**Status:** 📋 Ready for implementation with full composite support
**Risk:** Low (automatic fallback to v1.0.30 approach)
**Complexity:** Medium (3 methods + integration, ~110 lines)
**Key Difference from v1.0.33-40:** Metadata-first approach (decisions made upfront, not during hot path)
