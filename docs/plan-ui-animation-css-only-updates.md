# Plan: CSS-Only Updates - Lessons Learned & Next Approach

**Document Type:** Implementation Plan (Updated with v1.0.33-40 Experience)  
**Created:** 2025-10-26  
**Updated:** 2025-10-26 (Post-Rollback Analysis)  
**Status:** ⚠️ NEEDS REDESIGN - v1.0.33-40 rolled back to v1.0.30  
**Priority:** Medium (Stability achieved, performance is secondary)  
**Estimated Effort:** 8-12 hours (requires careful approach)  

## Executive Summary

**Attempted:** v1.0.33-40 implemented CSS-only updates for 100x performance improvement (150ms → 1ms)  
**Result:** ❌ Rolled back to v1.0.30 due to composite state reliability issues  
**Learning:** Performance gains don't justify stability loss for a monitoring tool  
**Status:** v1.0.41 uses stable v1.0.30 approach (full Mermaid re-render)

## What Went Wrong: v1.0.33-40 Post-Mortem

### Implementation Timeline
- **v1.0.33:** Initial CSS-only implementation - SVG enrichment + fast updates
- **v1.0.34:** Code cleanup - removed deprecated methods
- **v1.0.35:** CLI event field fix ('event_type' → 'type')
- **v1.0.36:** Fixed diagram switching and composite states
- **v1.0.37:** Fixed state- prefix mismatch (Mermaid vs backend naming)
- **v1.0.38:** Added composite state mapping logic
- **v1.0.39:** Added "is it composite" check (unnecessary)
- **v1.0.40:** Simplified composite logic back to v1.0.30 approach
- **v1.0.41:** 🔄 **ROLLBACK** to v1.0.30 - stability prioritized

### Critical Issues Discovered

#### 1. **Mermaid SVG ID Inconsistency**
```javascript
// Problem: Mermaid adds 'state-' prefix to node IDs
<g id="flowchart-state-monitoring_sdxl-123">
  <text>monitoring_sdxl</text>
</g>

// Backend sends clean names
{ to_state: "monitoring_sdxl" }

// Required 3-tier matching:
1. [data-state-id="monitoring_sdxl"]        // exact
2. [data-state-id="state-monitoring_sdxl"]  // with prefix
3. [data-state-clean="monitoring_sdxl"]     // fallback
```

#### 2. **Composite State Mapping Complexity**
```javascript
// Challenge: Backend sends individual states, UI shows composites on main diagram
Backend sends: "monitoring_sdxl"
Main diagram shows: "SDXLLIFECYCLE" composite (contains monitoring_sdxl)

// Required logic:
- Iterate metadata.diagrams to find which composite contains state
- If found, highlight composite instead of individual state
- Handle edge cases: standalone states, missing metadata, etc.
```

#### 3. **Diagram Switching Edge Cases**
```javascript
// Issue: Enrichment flag not cleared on diagram change
loadDiagram('main') → enriched=true
loadDiagram('SDXLLIFECYCLE') → still enriched=true (wrong!)
// New diagram has different states, old enrichment invalid

// Fix: Clear enrichment flag on every loadDiagram() call
this.container.dataset.enriched = 'false';
```

#### 4. **SVG Structure Assumptions**
```javascript
// Fragile: Relies on Mermaid's SVG structure not changing
const stateNodes = svg.querySelectorAll('g.node');
const edgeLabels = svg.querySelectorAll('g.edgeLabels g.label');

// Risk: Mermaid.js updates could break selectors
// Reality: Happened across v1.0.33-40 iterations
```

### What Worked Well

✅ **SVG Enrichment Concept**
- Adding `data-state-id`, `data-state-clean`, `data-edge-event` attributes
- Made DOM queries fast and debuggable
- Clear separation between structure and state

✅ **Fast Path Performance**
- CSS-only updates were genuinely ~1ms (100x faster)
- No flicker, smooth animations
- When it worked, it was excellent

✅ **Debugging Helpers**
```javascript
window.checkSvgEnrichment()  // Show enrichment status
window.forceReEnrich()        // Re-enrich current SVG
window.clearDiagramCache()    // Reset state
```

### What Didn't Work

❌ **Complexity vs Reliability Trade-off**
- 7 releases (v1.0.33-40) trying to fix edge cases
- Each fix introduced new issues
- Composite states never fully stable

❌ **Mermaid Assumptions**
- SVG structure is not guaranteed stable
- Node IDs have unpredictable prefixes
- Text content is most reliable but requires parsing

❌ **Metadata Dependency**
- Composite mapping requires `metadata.diagrams` structure
- Async loading race conditions
- Missing metadata = broken highlighting

## v1.0.30 Approach: Why It Works

### Simple & Reliable Architecture

```javascript
// 1. Fetch metadata asynchronously
async findCompositeForState(stateName) {
    const response = await fetch(`/api/diagram/${this.selectedMachine}/metadata`);
    const metadata = await response.json();
    
    for (const [compositeName, info] of Object.entries(metadata.diagrams)) {
        if (info.states && info.states.includes(stateName)) {
            return compositeName;
        }
    }
    return null;
}

// 2. Modify Mermaid diagram code with CSS classes
async renderDiagram(highlightState = null) {
    let diagramCode = this.currentDiagram;
    
    if (this.currentDiagramName === 'main') {
        const composite = await this.findCompositeForState(highlightState);
        if (composite) {
            diagramCode += `\n\n    classDef activeComposite fill:#FFD700,stroke:#FF8C00,stroke-width:4px`;
            diagramCode += `\n    class ${composite} activeComposite`;
        }
    } else {
        diagramCode += `\n\n    classDef active fill:#90EE90,stroke:#006400,stroke-width:4px`;
        diagramCode += `\n    class ${highlightState} active`;
    }
    
    // 3. Mermaid processes CSS classes natively
    await window.mermaid.run({ nodes: [mermaidEl] });
}
```

### Advantages
1. **Mermaid handles CSS natively** - no DOM manipulation
2. **Metadata fetched fresh** - no caching issues
3. **Composite logic centralized** - one place, simple
4. **No SVG structure assumptions** - works with any Mermaid version
5. **Proven in production** - v1.0.30 ran for weeks without issues

### Disadvantages
1. **Slower:** ~100-150ms per update vs 1ms
2. **Full re-render:** Entire SVG regenerated
3. **No animation reuse:** New SVG = new DOM elements

## Next Implementation Approach: Hybrid Strategy

### Goals
- ✅ Keep v1.0.30 stability
- ✅ Add CSS-only where it's safe
- ✅ Fall back to full render for edge cases

### Proposed Architecture

```mermaid
### Proposed Architecture

```mermaid
flowchart TD
    A[State Change Event] --> B{Diagram Type?}
    
    B -->|Subdiagram| C[Simple Case]
    B -->|Main Diagram| D[Complex Case]
    
    C --> E{State in current diagram?}
    E -->|Yes| F[✅ CSS-only update]
    E -->|No| G[❌ Fall back to full render]
    
    D --> H{State in metadata?}
    H -->|Yes| I{Composite exists in SVG?}
    I -->|Yes| J[✅ CSS-only composite highlight]
    I -->|No| K[❌ Fall back to full render]
    H -->|No| K
    
    F --> L[~1ms update]
    J --> M[~1ms update]
    K --> N[v1.0.30 full render ~150ms]
    G --> N
    
    style F fill:#90EE90,stroke:#006400
    style J fill:#90EE90,stroke:#006400
    style K fill:#FFD700,stroke:#FF8C00
    style G fill:#FFD700,stroke:#FF8C00
    style N fill:#87CEEB,stroke:#4682B4
```

### Implementation Strategy: Conservative Hybrid

#### Phase 1: Keep v1.0.30 as Foundation (Current - v1.0.41)
- ✅ DONE: Stable composite state highlighting
- ✅ DONE: Full Mermaid re-render approach
- ✅ DONE: All edge cases handled

#### Phase 2: Add CSS-Only for Subdiagrams ONLY (Low Risk)
**Rationale:** Subdiagrams are simple - no composites, direct state mapping

```javascript
async renderDiagram(highlightState = null, transition = null) {
    // Check if we can use CSS-only (ONLY for subdiagrams)
    if (this.currentDiagramName !== 'main' && 
        this.container.dataset.enriched === 'true' && 
        highlightState) {
        
        // FAST PATH: Subdiagram CSS-only update
        this.updateStateHighlight(highlightState, transition?.event);
        return;
    }
    
    // SLOW PATH: Full render (all main diagram updates + first subdiagram render)
    await this.fullMermaidRender(highlightState, transition);
}
```

**Why This Is Safe:**
- ✅ Subdiagrams show actual states (no composite mapping needed)
- ✅ State names match exactly (no prefix issues)
- ✅ Simpler SVG structure
- ✅ Fall back to full render on any failure

#### Phase 3: Add CSS-Only for Main Diagram Simple States (Medium Risk)
**Only after Phase 2 proven stable for 2+ weeks**

```javascript
// Only use CSS-only for standalone states on main diagram
if (this.currentDiagramName === 'main') {
    const compositeList = this.diagramMetadata?.diagrams?.main?.composites || [];
    
    // Is this state a standalone (not in any composite)?
    const isStandalone = !compositeList.includes(highlightState) && 
                        !this.belongsToComposite(highlightState);
    
    if (isStandalone && this.container.dataset.enriched === 'true') {
        // FAST PATH: Standalone state on main diagram
        this.updateStateHighlight(highlightState);
        return;
    }
}

// SLOW PATH: Use v1.0.30 approach for composites
await this.fullMermaidRender(highlightState, transition);
```

#### Phase 4: Composite States (High Risk - May Never Implement)
**Decision point:** Re-evaluate after Phases 2-3 are stable

**Blockers:**
- Composite mapping complexity (proven buggy in v1.0.33-40)
- Metadata dependencies
- SVG structure assumptions
- Edge cases with entry/exit states

**Alternative:** Accept 150ms for composite states, optimize only subdiagrams

### Risk Mitigation Strategies

#### 1. Feature Flags
```javascript
const ENABLE_CSS_ONLY_SUBDIAGRAMS = true;   // Phase 2
const ENABLE_CSS_ONLY_STANDALONE = false;    // Phase 3 (disabled by default)
const ENABLE_CSS_ONLY_COMPOSITES = false;    // Phase 4 (may never enable)
```

#### 2. Automatic Fallback on Failure
```javascript
updateStateHighlight(stateName) {
    try {
        const node = this.findStateNode(stateName);
        if (!node) {
            console.warn('[CSS-only] Node not found, falling back to full render');
            this.container.dataset.enriched = 'false';
            return false;  // Caller will trigger full render
        }
        // ... CSS update
        return true;
    } catch (error) {
        console.error('[CSS-only] Error, falling back:', error);
        this.container.dataset.enriched = 'false';
        return false;
    }
}
```

#### 3. Enrichment Validation
```javascript
enrichSvgWithDataAttributes() {
    const before = performance.now();
    
    // ... enrichment logic
    
    const enrichedNodes = svg.querySelectorAll('[data-state-id]').length;
    const after = performance.now();
    
    if (enrichedNodes === 0) {
        console.error('[Enrich] FAILED: No nodes enriched');
        return false;
    }
    
    console.log(`[Enrich] ✓ ${enrichedNodes} nodes in ${(after-before).toFixed(1)}ms`);
    return true;
}
```

#### 4. Performance Monitoring
```javascript
// Track which path is being used
window.diagramPerformanceStats = {
    cssOnlyUpdates: 0,
    fullRenders: 0,
    fallbacks: 0,
    avgCssTime: 0,
    avgRenderTime: 0
};
```

### Testing Strategy

#### Unit Tests (Before Implementation)
```javascript
describe('CSS-Only Subdiagram Updates', () => {
    it('should use CSS-only for subdiagram state changes', async () => {
        // Setup subdiagram
        await diagramManager.loadDiagram('machine1', 'PROCESSING');
        
        // First render (full)
        await diagramManager.updateState('generating');
        expect(fullRenderCalled).toBe(true);
        
        // Second render (CSS-only)
        await diagramManager.updateState('inpainting');
        expect(cssOnlyCalled).toBe(true);
        expect(fullRenderCalled).toBe(false);
    });
    
    it('should fallback to full render on enrichment failure', async () => {
        // Mock enrichment failure
        diagramManager.enrichSvgWithDataAttributes = () => false;
        
        await diagramManager.updateState('waiting');
        expect(fullRenderCalled).toBe(true);
    });
});
```

#### Integration Tests (Post-Implementation)
1. **Load subdiagram, trigger 10 state changes**
   - Expected: 1 full render + 9 CSS-only updates
   - Verify: No console errors, states highlighted correctly

2. **Switch between main and subdiagram**
   - Expected: Full render on each switch
   - Verify: Enrichment flag cleared on diagram load

3. **Composite states on main diagram**
   - Expected: Always use full render (v1.0.30 approach)
   - Verify: Correct composite highlighted

### Success Criteria

#### Phase 2 (Subdiagrams)#### Phase 2 (Subdiagrams)
- ✅ 95%+ of subdiagram updates use CSS-only path
- ✅ Zero console errors during 24-hour test
- ✅ States highlight correctly in all subdiagrams
- ✅ Automatic fallback works on edge cases
- ✅ Performance: <5ms average update time

#### Phase 3 (Standalone States on Main)
- ✅ Standalone states use CSS-only path
- ✅ Composites still use v1.0.30 full render
- ✅ No regressions in composite highlighting
- ✅ Zero errors over 1-week production test

#### Phase 4 (Composites) - Optional
- Decision: Re-evaluate based on Phase 2-3 stability
- May conclude: 150ms is acceptable for composite updates
- Alternative: Optimize Mermaid rendering instead

### Key Lessons Applied

1. **Start Simple, Add Complexity Gradually**
   - v1.0.33 tried to do everything at once → failed
   - New approach: Subdiagrams only first → prove stability → expand

2. **Always Have a Fallback**
   - CSS-only is optimization, not requirement
   - Full render as safety net on any failure

3. **Validate Assumptions**
   - Don't assume Mermaid SVG structure
   - Check enrichment succeeded before using it
   - Log everything for debugging

4. **Stability > Performance**
   - 150ms works fine for monitoring
   - 1ms is nice-to-have, not critical
   - Users don't notice 150ms, but DO notice bugs

5. **Composites Are Complex**
   - Mapping individual states → composites is hard
   - Metadata dependencies create race conditions
   - May not be worth optimizing

### Code Structure (Proposed Phase 2)

```javascript
class DiagramManager {
    constructor() {
        // Feature flags
        this.enableCssOnlySubdiagrams = true;  // Phase 2
        this.enableCssOnlyStandalone = false;  // Phase 3
        this.enableCssOnlyComposites = false;  // Phase 4 (likely never)
    }
    
    async renderDiagram(highlightState = null, transition = null) {
        // Attempt CSS-only update (safe cases only)
        if (this.canUseCssOnly(highlightState)) {
            const success = this.updateStateHighlight(highlightState, transition?.event);
            if (success) {
                console.log('[Render] ✓ CSS-only update (fast path)');
                return;
            }
            console.warn('[Render] CSS-only failed, falling back to full render');
        }
        
        // Full Mermaid render (v1.0.30 approach)
        await this.fullMermaidRender(highlightState, transition);
    }
    
    canUseCssOnly(highlightState) {
        if (!highlightState) return false;
        if (this.container.dataset.enriched !== 'true') return false;
        
        // Phase 2: Only subdiagrams
        if (this.enableCssOnlySubdiagrams && this.currentDiagramName !== 'main') {
            return true;
        }
        
        // Phase 3: Standalone states on main (disabled by default)
        if (this.enableCssOnlyStandalone && this.currentDiagramName === 'main') {
            return this.isStandaloneState(highlightState);
        }
        
        // Phase 4: Composites (disabled by default)
        if (this.enableCssOnlyComposites && this.currentDiagramName === 'main') {
            return true;  // Would need composite mapping logic
        }
        
        return false;
    }
    
    updateStateHighlight(stateName, eventName = null) {
        try {
            const svg = this.container.querySelector('svg');
            if (!svg) {
                console.warn('[CSS-only] No SVG found');
                return false;
            }
            
            // Remove old highlights
            svg.querySelectorAll('.active, .activeComposite').forEach(el => {
                el.classList.remove('active', 'activeComposite');
            });
            
            // Find and highlight new state
            const node = this.findStateNode(svg, stateName);
            if (!node) {
                console.warn(`[CSS-only] Node not found: ${stateName}`);
                this.container.dataset.enriched = 'false';  // Force re-enrich
                return false;
            }
            
            node.classList.add('active');
            console.log(`[CSS-only] ✓ Highlighted: ${stateName} (~1ms)`);
            
            // Highlight transition arrow
            if (eventName) {
                this.highlightTransitionArrow(svg, eventName);
            }
            
            return true;
        } catch (error) {
            console.error('[CSS-only] Error:', error);
            this.container.dataset.enriched = 'false';
            return false;
        }
    }
    
    findStateNode(svg, stateName) {
        // Try multiple selectors (most to least reliable)
        let node = svg.querySelector(`[data-state-id="${stateName}"]`);
        if (node) return node;
        
        node = svg.querySelector(`[data-state-clean="${stateName}"]`);
        if (node) return node;
        
        // Fallback: text content matching
        const textNodes = Array.from(svg.querySelectorAll('g.node text'));
        const matchingText = textNodes.find(t => t.textContent.trim() === stateName);
        if (matchingText) {
            return matchingText.closest('g.node');
        }
        
        return null;
    }
    
    async fullMermaidRender(highlightState = null, transition = null) {
        // v1.0.30 approach - proven stable
        let diagramCode = this.currentDiagram;
        
        if (highlightState) {
            if (this.currentDiagramName === 'main') {
                // Composite state handling
                const composite = await this.findCompositeForState(highlightState);
                if (composite) {
                    diagramCode += `\n\n    classDef activeComposite fill:#FFD700,stroke:#FF8C00,stroke-width:4px`;
                    diagramCode += `\n    class ${composite} activeComposite`;
                }
            } else {
                // Direct state highlighting
                diagramCode += `\n\n    classDef active fill:#90EE90,stroke:#006400,stroke-width:4px`;
                diagramCode += `\n    class ${highlightState} active`;
            }
        }
        
        // Render
        this.container.classList.add('redrawing');
        await new Promise(resolve => setTimeout(resolve, 50));
        this.container.innerHTML = `<pre class="mermaid">${diagramCode}</pre>`;
        
        const mermaidEl = this.container.querySelector('.mermaid');
        await window.mermaid.run({ nodes: [mermaidEl] });
        
        // Enrich for next CSS-only update
        if (this.enableCssOnlySubdiagrams || this.enableCssOnlyStandalone) {
            const enriched = this.enrichSvgWithDataAttributes();
            if (enriched) {
                this.container.dataset.enriched = 'true';
            }
        }
        
        this.container.classList.remove('redrawing');
        this.attachCompositeClickHandlers();
        
        console.log('[Render] ✓ Full Mermaid render (~150ms)');
    }
}
```

## Implementation Timeline

### Week 1: Preparation
- [ ] Set up feature flags
- [ ] Write unit tests for Phase 2
- [ ] Document current v1.0.30 behavior as baseline
- [ ] Create test plan for subdiagram updates

### Week 2: Phase 2 Implementation
- [ ] Implement `canUseCssOnly()` with subdiagram-only logic
- [ ] Implement enrichment with validation
- [ ] Implement `updateStateHighlight()` with fallback
- [ ] Manual testing with simple_worker example
- [ ] 24-hour stability test

### Week 3: Phase 2 Refinement
- [ ] Fix any issues found in testing
- [ ] Performance monitoring integration
- [ ] Documentation updates
- [ ] Release as v1.0.42 (conservative, feature-flagged)

### Week 4-5: Monitoring
- [ ] Monitor production usage
- [ ] Collect performance metrics
- [ ] Evaluate: Proceed to Phase 3 or stop here?

### Future: Phase 3 (TBD)
- Decision point after Phase 2 proven stable
- May conclude subdiagram optimization is sufficient
- Main diagram composites can stay with full render

## Appendix: v1.0.33-40 Detailed Changelog

### v1.0.33 (Initial CSS-only)
- Added `enrichSvgWithDataAttributes()`
- Added `updateStateHighlight()`
- Added enrichment flag checking
- **Issue:** Didn't clear flag on diagram switch

### v1.0.34 (Cleanup)
- Removed deprecated arrow highlighting methods
- ~136 lines of code removed
- **Issue:** No functional changes, cleanup only

### v1.0.35 (CLI Fix)
- Changed CLI event field 'event_type' → 'type'
- **Issue:** Unrelated to CSS-only updates

### v1.0.36 (Diagram Switching Fix)
- Clear enrichment flag in `loadDiagram()`
- Fixed composite state CSS class (`activeComposite`)
- **Issue:** Still had state name prefix mismatches

### v1.0.37 (Prefix Fix)
- Added `data-state-clean` attribute
- 3-tier matching strategy
- **Issue:** Composite state mapping still broken

### v1.0.38 (Composite Mapping)
- Added composite state detection
- Iterate `metadata.diagrams` to find parent composite
- **Issue:** Complex dual-check logic (unnecessary)

### v1.0.39 (Composite Check)
- Added "is it a composite" check
- **Issue:** Backend never sends composite names (check was useless)

### v1.0.40 (Simplification)
- Removed dual-check, back to single loop
- Enhanced logging
- **Issue:** Still unreliable with real composite states

### v1.0.41 (Rollback)
- 🔄 Complete rollback to v1.0.30
- Removed all CSS-only code
- Restored full Mermaid re-render approach
- **Result:** ✅ Stable again

## Conclusion

**Current Status:** v1.0.41 uses proven v1.0.30 approach - stable but slower

**Next Steps:**
1. Let v1.0.41 run in production for 2+ weeks
2. If stability confirmed, consider Phase 2 (subdiagram CSS-only)
3. Accept that main diagram composites may always use full render
4. Prioritize stability over performance

**Key Insight:** For a monitoring tool, seeing state changes reliably is more important than seeing them instantly. 150ms is acceptable. Bugs are not.

---

*Document updated: 2025-10-26 post v1.0.41 rollback*  
*Next review: After 2 weeks of v1.0.41 stability testing*
```

## Key Simplifications

### 1. No Version Hashing
- Don't hash diagram code to detect changes
- Simply: if Mermaid renders, enrich SVG
- If enriched SVG exists, use it

### 2. No Complex Cache Map
- Single flag: `this.svgEnriched = false`
- Enrich after every Mermaid render
- Update logic checks DOM directly

### 3. Parse Once, Update Many
- SVG parsing happens once per render
- All state changes use data attributes
- No repeated querySelector searches

### 4. Data Attributes for Easy Selection
- `data-state-id="state_name"` - Direct state selection
- `data-edge-event="event_name"` - Direct edge selection
- No complex ID matching patterns

## Implementation Tasks

### Phase 1: SVG Enrichment (2 hours)

- [ ] **Task 1.1:** Add `enrichSvgWithDataAttributes()` method
  - Called once after Mermaid.run() completes
  - Returns void (modifies SVG in-place)

- [ ] **Task 1.2:** Enrich state nodes with data-state-id
  - Find all SVG nodes matching state pattern
  - Extract state name from node ID or text content
  - Add `dataset.stateId = stateName`

- [ ] **Task 1.3:** Enrich edge paths with data-edge-event
  - Find all edge label elements (g.edgeLabels g.label)
  - Extract event name from label text
  - Find corresponding path by data-id
  - Add `dataset.edgeEvent = eventName` to path

- [ ] **Task 1.4:** Mark container as enriched
  - Add `data-enriched="true"` to container
  - Simple check: `this.container.dataset.enriched === 'true'`

### Phase 2: Simplified Update Logic (1.5 hours)

- [ ] **Task 2.1:** Add `updateStateHighlight(stateName)` method
  - Simple method with one parameter
  - No cache checks, no version checks
  - Just DOM manipulation

- [ ] **Task 2.2:** Remove old highlights
  - `querySelectorAll('.active, .activeComposite')`
  - `forEach(el => el.classList.remove(...))`

- [ ] **Task 2.3:** Add new highlight using data attribute
  - `querySelector('[data-state-id="${stateName}"]')`
  - `if (node) node.classList.add('active')`

- [ ] **Task 2.4:** Highlight transition arrow using data attribute
  - `querySelector('[data-edge-event="${eventName}"]')`
  - `if (edge) edge.classList.add('last-transition-arrow')`
  - Keep existing timeout cleanup

### Phase 3: Integration (1 hour)

- [ ] **Task 3.1:** Update `renderDiagram()` to call enrichment
  - After `mermaid.run()` succeeds
  - Call `enrichSvgWithDataAttributes()`
  - No other changes needed

- [ ] **Task 3.2:** Update `updateState()` to check if enriched
  - If `this.container.dataset.enriched === 'true'`
  - Call `updateStateHighlight()` and return early
  - Else fall back to `renderDiagram()`

- [ ] **Task 3.3:** Handle diagram structure changes
  - When new diagram loaded, enriched flag is cleared
  - Natural re-enrichment on next render
  - No manual cache invalidation needed

### Phase 4: Testing (1 hour)

- [ ] **Task 4.1:** Test state change after first render
  - Load diagram, verify enrichment
  - Change state, verify CSS-only update
  - Check data attributes in DevTools

- [ ] **Task 4.2:** Test rapid state changes
  - 10 state changes in quick succession
  - All should be CSS-only (~1ms each)
  - No flicker visible

- [ ] **Task 4.3:** Test composite state navigation
  - Navigate to subdiagram (new enrichment)
  - Change state in subdiagram (CSS-only)
  - Navigate back to main (new enrichment)

- [ ] **Task 4.4:** Test edge cases
  - State not found (graceful fallback)
  - Edge not found (no error, just no highlight)
  - Browser refresh (re-enrichment)

### Phase 5: Documentation (0.5 hours)

- [ ] **Task 5.1:** Add inline comments
  - Document enrichSvgWithDataAttributes()
  - Explain data attribute strategy
  - Note why this is simpler than caching

- [ ] **Task 5.2:** Update console logging
  - Log "SVG enriched with data attributes"
  - Log "CSS-only update" for fast path
  - Log "Full render" for slow path

- [ ] **Task 5.3:** Add debugging helper
  - `window.checkSvgEnrichment()` - shows all data attributes
  - `window.forceReEnrich()` - re-runs enrichment

## Implementation Code

### Core Enrichment Logic

```javascript
enrichSvgWithDataAttributes() {
    const svg = this.container.querySelector('svg');
    if (!svg) {
        console.warn('[Enrich] No SVG found');
        return;
    }
    
    let enrichedCount = 0;
    
    // 1. Enrich state nodes
    const stateNodes = svg.querySelectorAll('g.node');
    stateNodes.forEach(node => {
        // Extract state name from node ID or text
        const nodeId = node.id || '';
        const textEl = node.querySelector('text');
        const stateName = textEl ? textEl.textContent.trim() : 
                         nodeId.replace(/^flowchart-/, '').replace(/-\d+$/, '');
        
        if (stateName) {
            node.dataset.stateId = stateName;
            enrichedCount++;
        }
    });
    
    // 2. Enrich edge paths
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
    
    // 3. Mark as enriched
    this.container.dataset.enriched = 'true';
    console.log(`[Enrich] Added data attributes to ${enrichedCount} elements`);
}
```

### Simple Update Logic

```javascript
updateStateHighlight(stateName, eventName = null) {
    const svg = this.container.querySelector('svg');
    if (!svg) return;
    
    // Remove old highlights
    svg.querySelectorAll('.active, .activeComposite').forEach(el => {
        el.classList.remove('active', 'activeComposite');
    });
    
    // Add new highlight
    const stateNode = svg.querySelector(`[data-state-id="${stateName}"]`);
    if (stateNode) {
        stateNode.classList.add('active');
        console.log(`[CSS-only] Highlighted state: ${stateName}`);
    }
    
    // Highlight transition arrow
    if (eventName) {
        // Clear old arrow highlights
        svg.querySelectorAll('.last-transition-arrow').forEach(el => {
            el.classList.remove('last-transition-arrow');
        });
        
        const edge = svg.querySelector(`[data-edge-event="${eventName}"]`);
        if (edge) {
            edge.classList.add('last-transition-arrow');
            
            // Auto-clear after 2 seconds
            setTimeout(() => {
                edge.classList.remove('last-transition-arrow');
            }, 2000);
        }
    }
}
```

### Integration into renderDiagram()

```javascript
async renderDiagram(highlightState = null, transition = null) {
    // Check if we can use CSS-only update
    if (this.container.dataset.enriched === 'true' && highlightState) {
        const eventName = transition?.event;
        this.updateStateHighlight(highlightState, eventName);
        return; // FAST PATH - done in ~1ms
    }
    
    // SLOW PATH - full Mermaid render
    if (!this.currentDiagram) return;
    
    try {
        let diagramCode = this.currentDiagram;
        
        // ... existing fade effect logic ...
        this.container.classList.add('redrawing');
        await new Promise(resolve => setTimeout(resolve, 50));
        
        // Render with Mermaid
        this.container.innerHTML = `<pre class="mermaid">${diagramCode}</pre>`;
        const mermaidEl = this.container.querySelector('.mermaid');
        await window.mermaid.run({ nodes: [mermaidEl] });
        
        // ✨ NEW: Enrich SVG after render
        this.enrichSvgWithDataAttributes();
        
        // Remove fade effect
        this.container.classList.remove('redrawing');
        this.container.classList.add('has-diagram');
        
        // Attach handlers
        this.attachCompositeClickHandlers();
        
        // Initial highlight
        if (highlightState) {
            const eventName = transition?.event;
            this.updateStateHighlight(highlightState, eventName);
        }
        
    } catch (error) {
        console.error('Error rendering diagram:', error);
        this.container.dataset.enriched = 'false'; // Clear flag on error
    }
}
```

## Data Attribute Examples

**State Node (before enrichment):**
```html
<g class="node" id="flowchart-processing-123">
    <rect ...></rect>
    <text>processing</text>
</g>
```

**State Node (after enrichment):**
```html
<g class="node" id="flowchart-processing-123" data-state-id="processing">
    <rect ...></rect>
    <text>processing</text>
</g>
```

**Edge Path (before enrichment):**
```html
<path class="edge" data-id="L-waiting-processing-0" d="M..."></path>
```

**Edge Label:**
```html
<g class="label" data-id="L-waiting-processing-0">
    <text>new_job</text>
</g>
```

**Edge Path (after enrichment):**
```html
<path class="edge" data-id="L-waiting-processing-0" data-edge-event="new_job" d="M..."></path>
```

## Why This is Simpler

### Removed Complexity

❌ **No version hashing** - Was 20+ lines of hash logic  
❌ **No cache Map** - Was managing Map entries, LRU eviction  
❌ **No version comparison** - Was comparing hashes every update  
❌ **No cache invalidation** - Was clearing cache on various events  
❌ **No cache size limits** - Was tracking memory usage  

### Added Simplicity

✅ **Single enrichment flag** - Just `dataset.enriched === 'true'`  
✅ **Data attributes** - Browser-native, debuggable in DevTools  
✅ **Parse once** - Only after Mermaid renders  
✅ **Simple selectors** - Direct `[data-state-id="X"]` queries  
✅ **Natural invalidation** - New render = new enrichment  

### Code Comparison

**Before (complex caching):**
- getDiagramVersion(): 15 lines
- Cache management: 30 lines
- Version comparison: 10 lines
- Invalidation logic: 20 lines
- **Total: ~75 lines**

**After (data attributes):**
- enrichSvgWithDataAttributes(): 25 lines
- updateStateHighlight(): 15 lines
- Integration: 5 lines
- **Total: ~45 lines**

**Reduction: 40% less code**

## Performance Expectations

**First Render (or structure change):**
- Mermaid render: 100ms
- SVG enrichment: 5-10ms
- **Total: ~110ms** (10% slower than current, acceptable)

**State Change (enriched SVG):**
- querySelector: <1ms
- Class toggle: <1ms
- **Total: ~1ms** (100x faster than current)

**10 State Changes:**
- Before: 1000-1500ms (10 × 100-150ms)
- After: ~110ms first + 9×1ms = ~119ms
- **Speedup: 8-12x for typical usage**

## Testing Checklist

- [ ] First render enriches SVG with data attributes
- [ ] State change uses CSS-only update (check console log)
- [ ] 10 rapid state changes all use CSS-only
- [ ] Arrow highlighting works with data-edge-event
- [ ] Composite navigation re-enriches new diagram
- [ ] Breadcrumb navigation re-enriches when returning
- [ ] State not found doesn't break (graceful fallback)
- [ ] Event not found doesn't break (no arrow highlight)
- [ ] Browser refresh re-enriches on first render
- [ ] DevTools shows data-state-id attributes on nodes
- [ ] DevTools shows data-edge-event attributes on paths

## Success Criteria

**Must Have:**
- ✅ Zero flicker for state changes after first render
- ✅ <2ms update time for CSS-only path
- ✅ Data attributes visible in DevTools
- ✅ No regressions in arrow highlighting
- ✅ Code is simpler than current implementation

**Deal Breakers:**
- ❌ First render significantly slower (>120ms)
- ❌ Enrichment fails on complex diagrams
- ❌ Data attributes don't match state names

## Timeline

**Optimistic:** 3-4 hours  
**Realistic:** 4-6 hours  
**Pessimistic:** 6-8 hours  

**Single Session Approach:**
1. Hour 1: Implement enrichment (Tasks 1.1-1.4)
2. Hour 2: Implement update logic (Tasks 2.1-2.4)
3. Hour 3: Integration (Tasks 3.1-3.3)
4. Hour 4: Testing + debugging (Tasks 4.1-4.4)
5. Hour 5: Documentation (Task 5.1-5.3)

## Rollback Plan

**If enrichment fails:**
- Check `dataset.enriched === 'true'` will be false
- Falls back to full render automatically
- No worse than current behavior

**To disable entirely:**
```javascript
// At top of renderDiagram()
const ENABLE_CSS_ONLY_UPDATES = false; // Toggle here
if (!ENABLE_CSS_ONLY_UPDATES) {
    this.container.dataset.enriched = 'false';
}
```

## References

- **Parent Document:** `docs/ui-animation-implementation.md`
- **Related Issue:** Diagram flicker during repaint
- **Alternative Approach:** Double-buffering (simpler but less optimal)

---

**Status:** 📋 Ready for implementation  
**Complexity:** Low (simple DOM manipulation)  
**Risk:** Low (graceful fallback to current behavior)  
**Last Updated:** 2025-10-26
