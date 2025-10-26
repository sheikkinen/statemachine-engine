# Diagram Test Harness - Simple Implementation Plan

## Problem Statement

We're doing trial-and-error debugging. We need:
1. **Real SVG from production** - We have it: `sdxlgenerationphase-svg.md`
2. **Simple test with real data** - Parse the actual SVG structure
3. **Clear logging** - See exactly what matches and what doesn't

## Starting Point: Real Production Data

### What We Have
- **Real SVG**: `docs/sdxlgenerationphase-svg.md` (coordinates stripped, 28KB)
- **Real metadata**: SDXLGENERATIONPHASE states
- **Real error**: "Node not found for scaling_image"

### SVG Structure (from production)
```html
<g class="node  statediagram-state" id="state-switching_to_sdxl-1">
<g class="node  statediagram-state" id="state-enhancing_prompt-3">
<g class="node  statediagram-state" id="state-updating_job_prompt-5">
<g class="node  statediagram-state" id="state-generating_fallback_image-7">
<g class="node  statediagram-state" id="state-generating_enhanced_image-6">
<g class="node  statediagram-state" id="state-early_face_detection-9">
<g class="node  statediagram-state" id="state-scaling_image-10">
<g class="node  statediagram-state" id="state-COMPLETIONPHASE-10">
```

**Key observations**:
- ✅ Class: `"node  statediagram-state"` (double space between node and statediagram-state)
- ✅ ID pattern: `state-{name}-{number}`
- ✅ Selector `g.node, g.statediagram-state` SHOULD match
- ⚠️ Text is in nested `<foreignObject><div><span class="nodeLabel"><p>text</p></span></div></foreignObject>`

## Simple Implementation Plan

### Step 1: Enhanced Logging (30 min)

Add detailed logging to `enrichSvgWithDataAttributes()` to see EXACTLY what's happening:

```javascript
// In DiagramManager.js enrichSvgWithDataAttributes()

enrichSvgWithDataAttributes() {
    const startTime = Date.now();
    const svg = this.container.querySelector('svg');
    if (!svg) {
        console.warn('[Enrich] No SVG found');
        return false;
    }

    let enrichedCount = 0;
    const targets = new Set(Object.values(this.stateHighlightMap).map(e => e.target));
    const enrichedNodes = [];
    const failedNodes = [];

    console.group('[Enrich] Starting enrichment');
    console.log('Targets to enrich:', Array.from(targets));

    // Find all nodes
    const stateNodes = svg.querySelectorAll('g.node, g.statediagram-state');
    console.log(`Found ${stateNodes.length} nodes with selector 'g.node, g.statediagram-state'`);

    // Try to enrich each node
    stateNodes.forEach((node, index) => {
        const textEl = node.querySelector('text');
        const stateName = textEl ? textEl.textContent.trim() : '';
        
        const nodeInfo = {
            index,
            id: node.id,
            classes: node.className.baseVal || node.getAttribute('class'),
            textContent: stateName,
            isTarget: targets.has(stateName)
        };

        if (stateName && targets.has(stateName)) {
            node.dataset.stateId = stateName;
            enrichedCount++;
            enrichedNodes.push(nodeInfo);
        } else {
            failedNodes.push(nodeInfo);
        }
    });

    // Detailed reporting
    console.log(`✅ Enriched: ${enrichedCount}/${targets.size}`);
    
    if (enrichedNodes.length > 0) {
        console.table(enrichedNodes);
    }
    
    if (failedNodes.length > 0) {
        console.warn(`❌ Not enriched: ${failedNodes.length} nodes`);
        console.table(failedNodes);
    }
    
    // Check for missing targets
    const enrichedTargets = new Set(enrichedNodes.map(n => n.textContent));
    const missingTargets = Array.from(targets).filter(t => !enrichedTargets.has(t));
    if (missingTargets.length > 0) {
        console.error('⚠️ Targets not found in SVG:', missingTargets);
    }

    console.groupEnd();
    
    return enrichedCount > 0;
}
```

### Step 2: Real SVG Test (30 min)

Create ONE test with the actual production SVG:

```javascript
// tests/DiagramManager.realsvg.test.js

import { DiagramManager } from '../modules/DiagramManager.js';
import { readFileSync } from 'fs';
import { join } from 'path';

describe('Real SDXL SVG from Production', () => {
    let manager, container;
    
    beforeEach(() => {
        // Load REAL SVG from production
        const svgContent = readFileSync(
            join(__dirname, '../../docs/sdxlgenerationphase-svg.md'),
            'utf-8'
        );
        
        container = document.createElement('div');
        container.innerHTML = svgContent;
        
        const breadcrumb = document.createElement('nav');
        const logger = { log: () => {} };
        manager = new DiagramManager(container, breadcrumb, logger);
        
        // Real metadata
        manager.diagramMetadata = {
            diagrams: {
                SDXLGENERATIONPHASE: {
                    states: [
                        'switching_to_sdxl',
                        'enhancing_prompt',
                        'updating_job_prompt',
                        'generating_fallback_image',
                        'generating_enhanced_image',
                        'early_face_detection',
                        'scaling_image'
                    ]
                }
            }
        };
        manager.currentDiagramName = 'SDXLGENERATIONPHASE';
    });
    
    it('should find all state nodes', () => {
        const svg = container.querySelector('svg');
        const nodes = svg.querySelectorAll('g.node, g.statediagram-state');
        
        // We know from analysis there are 8 nodes
        expect(nodes.length).toBeGreaterThan(0);
        
        // Log what we found
        nodes.forEach((node, i) => {
            console.log(`Node ${i}:`, {
                id: node.id,
                classes: node.className.baseVal,
                text: node.querySelector('text')?.textContent?.trim()
            });
        });
    });
    
    it('should enrich all SDXL states', () => {
        // Build map
        manager.stateHighlightMap = manager.buildStateHighlightMap();
        console.log('State map:', manager.stateHighlightMap);
        
        // Enrich (with detailed logging)
        const enriched = manager.enrichSvgWithDataAttributes();
        
        // Should have enriched something
        expect(enriched).toBe(true);
        
        // Check each expected state
        const expectedStates = [
            'early_face_detection',
            'scaling_image',
            'generating_enhanced_image'
        ];
        
        expectedStates.forEach(stateName => {
            const node = container.querySelector(`[data-state-id="${stateName}"]`);
            if (!node) {
                console.error(`❌ Missing: ${stateName}`);
                
                // Try to find it by text
                const allText = Array.from(container.querySelectorAll('text'))
                    .map(t => t.textContent.trim());
                console.log('All text in SVG:', allText);
            }
            expect(node).not.toBeNull();
        });
    });
    
    it('should use fast path after enrichment', () => {
        // Setup
        manager.stateHighlightMap = manager.buildStateHighlightMap();
        manager.enrichSvgWithDataAttributes();
        container.dataset.enriched = 'true';
        
        // Try fast path for scaling_image (the failing state)
        const success = manager.updateStateHighlight('scaling_image');
        
        if (!success) {
            console.error('Fast path failed for scaling_image');
            console.log('Looking for node with data-state-id="scaling_image"');
            
            const allEnriched = container.querySelectorAll('[data-state-id]');
            console.log('All enriched nodes:', Array.from(allEnriched).map(n => ({
                id: n.id,
                dataStateId: n.dataset.stateId
            })));
        }
        
        expect(success).toBe(true);
    });
});
```

### Step 3: Run & Debug (15 min)

```bash
# Run the test
cd src/statemachine_engine/ui
npm test -- DiagramManager.realsvg.test.js

# This will show EXACTLY:
# 1. What nodes exist in the SVG
# 2. What text content they have
# 3. Which ones got enriched
# 4. Which targets are missing
# 5. Why fast path fails
```

## Expected Outcome

The test will reveal ONE of these:

1. **Text content mismatch** - The `<text>` element doesn't contain the state name
   - Fix: Use ID parsing as fallback (`state-scaling_image-10` → `scaling_image`)

2. **Selector doesn't match** - querySelectorAll returns empty
   - Fix: Update selector (but we already did this)

3. **Nested text structure** - Text is in `<p>` not `<text>`
   - Fix: Check `node.querySelector('p')` instead of `node.querySelector('text')`

4. **Something else** - The logs will tell us exactly what

## Timeline

- ✅ **Done**: Captured real SVG, stripped coordinates
- **Next 30 min**: Add enhanced logging
- **Next 30 min**: Create real SVG test
- **Next 15 min**: Run test, see results
- **Next 30 min**: Fix based on what we learn

**Total: ~2 hours to definitive answer**

## Why This Works

1. **No guessing** - Using actual production SVG
2. **No synthesis** - Not creating fake test data
3. **Clear feedback** - Logs show exactly what's wrong
4. **One test** - Focus on the actual failing case
5. **Iterative** - Test → See logs → Fix → Repeat

## Next Steps After This Works

Once we understand the issue:
1. Fix enrichment logic based on findings
2. Add similar test for flowchart diagrams
3. Add test for main diagram with composites
4. Clean up and commit

---

**Key Principle**: Use real data, add logging, let the data tell us what's wrong.


## Problem Statement

We've been doing trial-and-error debugging for CSS-only fast path issues. We need:
1. **Real SVG fixtures** - Actual Mermaid-rendered SVG from production
2. **Comprehensive logging** - Full visibility into enrichment and matching
3. **Deterministic tests** - No guessing, clear pass/fail criteria
4. **SVG inspection tools** - Utilities to analyze diagram structure

## Root Cause Analysis

The issue: We're testing with **synthetic SVG** that doesn't match **real Mermaid output**.

### Current Test Problems
```javascript
// ❌ Synthetic SVG - doesn't match real Mermaid structure
const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
g.setAttribute('class', 'node statediagram-state');
g.setAttribute('id', `state-${stateName}-10`);
```

**Real Mermaid v11 output** may have:
- Different ID formats
- Nested text elements
- Additional wrapper elements
- Different class combinations
- Version-specific quirks

## Solution: Capture Real Production SVG

### Phase 1: SVG Fixture Capture System

#### 1.1 Browser-Based SVG Capture Tool
Create a utility to capture actual rendered SVG from running UI:

```javascript
// src/statemachine_engine/ui/public/modules/SvgCapture.js

export class SvgCapture {
    /**
     * Capture SVG from current diagram container
     * Strips coordinates, preserves structure
     */
    static captureCurrentDiagram() {
        const svg = document.querySelector('.diagram-container svg');
        if (!svg) return null;
        
        const clone = svg.cloneNode(true);
        
        // Strip coordinate noise but keep IDs and classes
        this.stripCoordinates(clone);
        
        // Extract metadata
        const metadata = {
            nodeCount: clone.querySelectorAll('g.node, g.statediagram-state').length,
            edgeCount: clone.querySelectorAll('path.transition, path.edge').length,
            classes: this.extractUniqueClasses(clone),
            ids: this.extractNodeIds(clone),
            mermaidVersion: this.detectMermaidVersion(clone)
        };
        
        return {
            svg: clone.outerHTML,
            metadata,
            timestamp: new Date().toISOString()
        };
    }
    
    /**
     * Strip verbose coordinate attributes
     */
    static stripCoordinates(element) {
        // Remove transform coordinates but keep structure
        const transforms = element.querySelectorAll('[transform]');
        transforms.forEach(el => {
            // Replace "translate(123.456, 789.012)" with "translate(X, Y)"
            const transform = el.getAttribute('transform');
            if (transform && transform.includes('translate')) {
                el.setAttribute('transform', 'translate(X, Y)');
            }
        });
        
        // Remove d attribute from paths (verbose coordinates)
        element.querySelectorAll('path[d]').forEach(path => {
            path.setAttribute('d', 'PATH_DATA');
        });
        
        // Remove viewBox (keep width/height)
        if (element.hasAttribute('viewBox')) {
            element.setAttribute('viewBox', '0 0 W H');
        }
        
        return element;
    }
    
    /**
     * Extract all unique CSS classes used
     */
    static extractUniqueClasses(svg) {
        const classes = new Set();
        svg.querySelectorAll('[class]').forEach(el => {
            el.className.baseVal.split(' ').forEach(cls => {
                if (cls) classes.add(cls);
            });
        });
        return Array.from(classes).sort();
    }
    
    /**
     * Extract all node IDs and their patterns
     */
    static extractNodeIds(svg) {
        const ids = [];
        svg.querySelectorAll('g.node, g.statediagram-state').forEach(node => {
            ids.push({
                id: node.id,
                pattern: this.analyzeIdPattern(node.id),
                classes: node.className.baseVal,
                textContent: node.querySelector('text')?.textContent?.trim()
            });
        });
        return ids;
    }
    
    /**
     * Detect ID pattern: flowchart-X-N vs state-X-N vs X
     */
    static analyzeIdPattern(id) {
        if (id.match(/^flowchart-.*-\d+$/)) return 'flowchart-NAME-NUM';
        if (id.match(/^state-.*-\d+$/)) return 'state-NAME-NUM';
        if (id.match(/^.*-\d+$/)) return 'NAME-NUM';
        return 'OTHER';
    }
    
    /**
     * Detect Mermaid version from SVG structure
     */
    static detectMermaidVersion(svg) {
        // v11+ uses statediagram-state
        if (svg.querySelector('.statediagram-state')) return 'v11+';
        // v10 uses different markers
        if (svg.querySelector('.mermaid-v10')) return 'v10';
        return 'unknown';
    }
    
    /**
     * Download fixture as JSON
     */
    static downloadFixture(name, data) {
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${name}-fixture.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

// Add to window for console access
window.SvgCapture = SvgCapture;

// Keyboard shortcut: Ctrl+Shift+S to capture
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'S') {
        const data = SvgCapture.captureCurrentDiagram();
        if (data) {
            console.log('Captured diagram:', data);
            SvgCapture.downloadFixture('diagram', data);
        }
    }
});
```

#### 1.2 Fixture Storage Structure
```
tests/fixtures/
├── README.md                           # How to capture and use fixtures
├── flowchart-main-simple.json         # Simple flowchart diagram
├── flowchart-main-composite.json      # Main with composite states
├── statediagram-sdxl-generation.json  # SDXLGENERATIONPHASE subdiagram
├── statediagram-queue-mgmt.json       # QUEUEMANAGEMENT subdiagram
└── mixed-diagram.json                 # Mixed flowchart + statediagram
```

Each fixture JSON:
```json
{
  "name": "sdxl-generation-phase",
  "description": "Real SDXLGENERATIONPHASE composite subdiagram from production",
  "captured": "2025-10-26T12:00:00Z",
  "mermaidVersion": "v11+",
  "metadata": {
    "nodeCount": 7,
    "edgeCount": 6,
    "classes": ["edgeLabel", "edgePath", "node", "statediagram-state", "transition"],
    "ids": [
      {
        "id": "state-early_face_detection-10",
        "pattern": "state-NAME-NUM",
        "classes": "node statediagram-state",
        "textContent": "early_face_detection"
      }
    ]
  },
  "diagramMetadata": {
    "diagrams": {
      "SDXLGENERATIONPHASE": {
        "states": [
          "early_face_detection",
          "generating_enhanced_image",
          "scaling_image",
          "face_detection",
          "processing_faces",
          "face_replacement",
          "image_generation_complete"
        ]
      }
    }
  },
  "svg": "<svg>...stripped coordinates...</svg>"
}
```

### Phase 2: Enhanced Logging System

#### 2.1 Structured Enrichment Logging
Replace console.log with structured logger:

```javascript
// public/modules/EnrichmentLogger.js

export class EnrichmentLogger {
    constructor(enabled = true) {
        this.enabled = enabled;
        this.history = [];
    }
    
    /**
     * Log enrichment attempt with full context
     */
    logEnrichment(container, stateHighlightMap) {
        if (!this.enabled) return;
        
        const svg = container.querySelector('svg');
        if (!svg) {
            this.warn('No SVG found in container');
            return;
        }
        
        const report = {
            timestamp: Date.now(),
            selector: 'g.node, g.statediagram-state',
            
            // What we're looking for
            targetStates: Object.keys(stateHighlightMap),
            
            // What we found in DOM
            allNodes: this.analyzeNodes(svg),
            
            // Match results
            matches: [],
            misses: []
        };
        
        // Analyze each target state
        Object.entries(stateHighlightMap).forEach(([stateName, entry]) => {
            const node = svg.querySelector(`[data-state-id="${entry.target}"]`);
            
            if (node) {
                report.matches.push({
                    state: stateName,
                    target: entry.target,
                    foundById: node.id,
                    classes: node.className.baseVal,
                    textContent: node.querySelector('text')?.textContent?.trim()
                });
            } else {
                // Deep analysis of miss
                report.misses.push({
                    state: stateName,
                    target: entry.target,
                    possibleCandidates: this.findCandidates(svg, entry.target)
                });
            }
        });
        
        this.history.push(report);
        this.printReport(report);
        
        return report;
    }
    
    /**
     * Analyze all nodes in SVG
     */
    analyzeNodes(svg) {
        const nodes = svg.querySelectorAll('g.node, g.statediagram-state');
        return Array.from(nodes).map(node => ({
            id: node.id,
            classes: node.className.baseVal,
            textContent: node.querySelector('text')?.textContent?.trim(),
            hasDataStateId: node.hasAttribute('data-state-id'),
            dataStateId: node.dataset.stateId || null,
            parent: node.parentElement?.tagName,
            childCount: node.children.length
        }));
    }
    
    /**
     * Find potential matching nodes for a missed state
     */
    findCandidates(svg, targetName) {
        const candidates = [];
        const nodes = svg.querySelectorAll('g.node, g.statediagram-state');
        
        nodes.forEach(node => {
            const text = node.querySelector('text')?.textContent?.trim();
            const id = node.id;
            
            // Check if ID contains target name
            if (id.includes(targetName)) {
                candidates.push({
                    reason: 'ID contains target',
                    node: {
                        id,
                        classes: node.className.baseVal,
                        text
                    }
                });
            }
            
            // Check if text matches
            if (text === targetName) {
                candidates.push({
                    reason: 'Text matches exactly',
                    node: {
                        id,
                        classes: node.className.baseVal,
                        text
                    }
                });
            }
            
            // Check partial match
            if (text && targetName.includes(text)) {
                candidates.push({
                    reason: 'Text partial match',
                    node: {
                        id,
                        classes: node.className.baseVal,
                        text
                    }
                });
            }
        });
        
        return candidates;
    }
    
    /**
     * Print structured report
     */
    printReport(report) {
        console.group(`[Enrichment] ${report.matches.length}/${report.targetStates.length} matched`);
        
        console.log('🎯 Targets:', report.targetStates);
        console.log('🔍 Found nodes:', report.allNodes.length);
        
        if (report.matches.length > 0) {
            console.group('✅ Matches:');
            console.table(report.matches);
            console.groupEnd();
        }
        
        if (report.misses.length > 0) {
            console.group('❌ Misses:');
            report.misses.forEach(miss => {
                console.log(`State: ${miss.state} → Target: ${miss.target}`);
                if (miss.possibleCandidates.length > 0) {
                    console.log('  Possible candidates:');
                    console.table(miss.possibleCandidates);
                } else {
                    console.log('  No candidates found!');
                }
            });
            console.groupEnd();
        }
        
        console.groupEnd();
    }
    
    /**
     * Export history for debugging
     */
    exportHistory() {
        return {
            totalEnrichments: this.history.length,
            history: this.history
        };
    }
    
    warn(message) {
        console.warn(`[EnrichmentLogger] ${message}`);
    }
}
```

#### 2.2 Integration into DiagramManager
```javascript
// In DiagramManager constructor
this.enrichmentLogger = new EnrichmentLogger(true);

// In enrichSvgWithDataAttributes()
enrichSvgWithDataAttributes() {
    // ... existing code ...
    
    // Log with full analysis
    const report = this.enrichmentLogger.logEnrichment(
        this.container, 
        this.stateHighlightMap
    );
    
    // Determine success
    return report.matches.length > 0;
}
```

### Phase 3: Fixture-Based Test Suite

#### 3.1 Test Harness
```javascript
// tests/harness/DiagramTestHarness.js

export class DiagramTestHarness {
    /**
     * Load fixture from JSON
     */
    static async loadFixture(name) {
        const response = await fetch(`/tests/fixtures/${name}.json`);
        return await response.json();
    }
    
    /**
     * Create container with real SVG
     */
    static createContainerWithFixture(fixture) {
        const container = document.createElement('div');
        container.innerHTML = fixture.svg;
        return container;
    }
    
    /**
     * Create DiagramManager with fixture
     */
    static createDiagramManagerWithFixture(fixture) {
        const container = this.createContainerWithFixture(fixture);
        const breadcrumb = document.createElement('nav');
        const logger = { log: () => {} };
        
        const manager = new DiagramManager(container, breadcrumb, logger);
        manager.diagramMetadata = fixture.diagramMetadata;
        manager.currentDiagramName = Object.keys(fixture.diagramMetadata.diagrams)[0];
        
        return { manager, container };
    }
    
    /**
     * Assert enrichment worked correctly
     */
    static assertEnrichment(container, expectedStates) {
        const svg = container.querySelector('svg');
        const results = {
            expected: expectedStates,
            found: [],
            missing: []
        };
        
        expectedStates.forEach(stateName => {
            const node = svg.querySelector(`[data-state-id="${stateName}"]`);
            if (node) {
                results.found.push({
                    state: stateName,
                    id: node.id,
                    classes: node.className.baseVal
                });
            } else {
                results.missing.push(stateName);
            }
        });
        
        return results;
    }
    
    /**
     * Diff two SVG structures (for debugging)
     */
    static diffSvg(actualSvg, expectedSvg) {
        const actual = this.extractStructure(actualSvg);
        const expected = this.extractStructure(expectedSvg);
        
        return {
            nodesAdded: expected.nodes.filter(n => !actual.nodes.includes(n)),
            nodesRemoved: actual.nodes.filter(n => !expected.nodes.includes(n)),
            classesAdded: expected.classes.filter(c => !actual.classes.includes(c)),
            classesRemoved: actual.classes.filter(c => !expected.classes.includes(c))
        };
    }
    
    static extractStructure(svg) {
        return {
            nodes: Array.from(svg.querySelectorAll('g')).map(g => g.id),
            classes: this.extractUniqueClasses(svg)
        };
    }
}
```

#### 3.2 Fixture-Based Tests
```javascript
// tests/DiagramManager.fixtures.test.js

import { DiagramManager } from '../modules/DiagramManager.js';
import { DiagramTestHarness } from './harness/DiagramTestHarness.js';

describe('DiagramManager - Real SVG Fixtures', () => {
    
    describe('SDXL Generation Phase (statediagram)', () => {
        let fixture, manager, container;
        
        beforeAll(async () => {
            fixture = await DiagramTestHarness.loadFixture('statediagram-sdxl-generation');
        });
        
        beforeEach(() => {
            const setup = DiagramTestHarness.createDiagramManagerWithFixture(fixture);
            manager = setup.manager;
            container = setup.container;
        });
        
        it('should match fixture metadata', () => {
            const svg = container.querySelector('svg');
            const nodes = svg.querySelectorAll('g.node, g.statediagram-state');
            
            expect(nodes.length).toBe(fixture.metadata.nodeCount);
            expect(fixture.metadata.classes).toContain('statediagram-state');
        });
        
        it('should enrich all states from fixture', () => {
            // Build map
            manager.stateHighlightMap = manager.buildStateHighlightMap();
            
            // Enrich
            const enriched = manager.enrichSvgWithDataAttributes();
            expect(enriched).toBe(true);
            
            // Verify all states enriched
            const expectedStates = fixture.diagramMetadata.diagrams.SDXLGENERATIONPHASE.states;
            const results = DiagramTestHarness.assertEnrichment(container, expectedStates);
            
            expect(results.found.length).toBe(expectedStates.length);
            expect(results.missing).toEqual([]);
            
            // Log details for debugging
            if (results.missing.length > 0) {
                console.error('Missing enrichment for:', results.missing);
                console.log('Found:', results.found);
            }
        });
        
        it('should use fast path for state changes', () => {
            // Setup
            manager.stateHighlightMap = manager.buildStateHighlightMap();
            manager.enrichSvgWithDataAttributes();
            container.dataset.enriched = 'true';
            
            // Test each state from fixture
            const states = fixture.diagramMetadata.diagrams.SDXLGENERATIONPHASE.states;
            states.forEach(stateName => {
                const success = manager.updateStateHighlight(stateName);
                expect(success).toBe(true);
                
                const node = container.querySelector(`[data-state-id="${stateName}"]`);
                expect(node).not.toBeNull();
                expect(node.classList.contains('active')).toBe(true);
            });
        });
    });
    
    describe('Flowchart vs Statediagram differences', () => {
        it('should handle both diagram types', async () => {
            const flowchartFixture = await DiagramTestHarness.loadFixture('flowchart-main-composite');
            const statediagramFixture = await DiagramTestHarness.loadFixture('statediagram-sdxl-generation');
            
            // Flowchart should have 'node' class
            expect(flowchartFixture.metadata.classes).toContain('node');
            
            // Statediagram should have 'statediagram-state' class
            expect(statediagramFixture.metadata.classes).toContain('statediagram-state');
            
            // Both should enrich successfully
            const fc = DiagramTestHarness.createDiagramManagerWithFixture(flowchartFixture);
            fc.manager.stateHighlightMap = fc.manager.buildStateHighlightMap();
            expect(fc.manager.enrichSvgWithDataAttributes()).toBe(true);
            
            const sd = DiagramTestHarness.createDiagramManagerWithFixture(statediagramFixture);
            sd.manager.stateHighlightMap = sd.manager.buildStateHighlightMap();
            expect(sd.manager.enrichSvgWithDataAttributes()).toBe(true);
        });
    });
});
```

## Implementation Plan

### Week 1: Capture Infrastructure
1. **Day 1-2**: Implement `SvgCapture.js`
   - Add to DiagramManager imports
   - Test capture on running UI
   - Verify coordinate stripping works

2. **Day 3-4**: Capture production fixtures
   - Run actual state machines
   - Capture main diagram (flowchart)
   - Capture SDXLGENERATIONPHASE (statediagram)
   - Capture QUEUEMANAGEMENT (statediagram)
   - Capture mixed scenarios

3. **Day 5**: Validate fixtures
   - Manual inspection of JSON
   - Compare metadata with expectations
   - Document any surprises

### Week 2: Enhanced Logging
1. **Day 1-2**: Implement `EnrichmentLogger.js`
   - Structured logging
   - Match/miss analysis
   - Candidate detection

2. **Day 3-4**: Integration
   - Replace console.log in DiagramManager
   - Test on running UI
   - Verify reports are actionable

### Week 3: Test Harness
1. **Day 1-2**: Implement `DiagramTestHarness.js`
   - Fixture loading
   - Container setup
   - Assertion helpers

2. **Day 3-5**: Write fixture-based tests
   - Test each captured fixture
   - Verify enrichment
   - Verify fast path

### Week 4: Debugging & Documentation
1. **Day 1-3**: Fix issues found by tests
   - Address any enrichment failures
   - Fix selector issues
   - Handle edge cases

2. **Day 4-5**: Documentation
   - How to capture fixtures
   - How to write fixture tests
   - Debugging guide

## Success Criteria

✅ **No more trial-and-error**
- Tests use real production SVG
- Clear pass/fail on enrichment
- Detailed logs show exactly what failed

✅ **Comprehensive coverage**
- Flowchart diagrams tested
- Statediagram diagrams tested
- Mixed diagrams tested
- Main + subdiagram navigation tested

✅ **Maintainable**
- Easy to capture new fixtures
- Clear test structure
- Self-documenting logs

## Future Enhancements

1. **Visual diff tool** - Compare expected vs actual SVG visually
2. **Regression suite** - Capture before/after fixtures for changes
3. **Performance benchmarks** - Track enrichment and fast path timing
4. **Mermaid version matrix** - Test against multiple Mermaid versions

## References

- Current issue: `docs/issue-css.md`
- DiagramManager: `src/statemachine_engine/ui/public/modules/DiagramManager.js`
- Existing tests: `src/statemachine_engine/ui/public/tests/DiagramManager.*.test.js`
