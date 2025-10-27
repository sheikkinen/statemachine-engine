/**
 * Unit Tests for DiagramManager - CSS-Only Updates with Composite Support
 * Tests the metadata-driven approach for fast state highlighting
 */

import { DiagramManager } from '../modules/DiagramManager.js';

describe('buildStateHighlightMap', () => {
    let diagramManager;

    beforeEach(() => {
        const container = document.createElement('div');
        const breadcrumb = document.createElement('nav');
        const logger = { log: () => {} };
        diagramManager = new DiagramManager(container, breadcrumb, logger);
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
        expect(Object.keys(map).length).toBe(6); // 2 composites + 4 substates

        // Composites should map to themselves
        expect(map['SDXLLIFECYCLE']).toEqual({
            type: 'composite',
            target: 'SDXLLIFECYCLE',
            class: 'activeComposite'
        });

        expect(map['QUEUEMANAGEMENT']).toEqual({
            type: 'composite',
            target: 'QUEUEMANAGEMENT',
            class: 'activeComposite'
        });

        // Substates should map to their parent composite
        expect(map['monitoring_sdxl']).toEqual({
            type: 'composite',
            target: 'SDXLLIFECYCLE',
            class: 'activeComposite'
        });

        expect(map['completing_sdxl']).toEqual({
            type: 'composite',
            target: 'SDXLLIFECYCLE',
            class: 'activeComposite'
        });

        expect(map['checking_queue']).toEqual({
            type: 'composite',
            target: 'QUEUEMANAGEMENT',
            class: 'activeComposite'
        });

        expect(map['dispatching']).toEqual({
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

        expect(map['completing_sdxl']).toEqual({
            type: 'state',
            target: 'completing_sdxl',
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

    it('should handle empty composites array', () => {
        diagramManager.diagramMetadata = {
            diagrams: {
                main: { composites: [] }
            }
        };
        diagramManager.currentDiagramName = 'main';

        const map = diagramManager.buildStateHighlightMap();

        expect(map).toEqual({});
    });

    it('should handle missing states array in composite', () => {
        diagramManager.diagramMetadata = {
            diagrams: {
                main: { composites: ['TEST'] },
                TEST: { } // No states array
            }
        };
        diagramManager.currentDiagramName = 'main';

        const map = diagramManager.buildStateHighlightMap();

        // Even with no substates, composite should map to itself
        expect(map).toEqual({
            TEST: {
                type: 'composite',
                target: 'TEST',
                class: 'activeComposite'
            }
        });
    });
});

describe('enrichSvgWithDataAttributes', () => {
    let diagramManager;

    beforeEach(() => {
        const container = document.createElement('div');
        const breadcrumb = document.createElement('nav');
        const logger = { log: () => {} };
        diagramManager = new DiagramManager(container, breadcrumb, logger);

        // Create mock SVG structure
        container.innerHTML = `
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
                    <g class="label" data-id="L-processing-done-1">
                        <text>job_complete</text>
                    </g>
                </g>
                <path data-id="L-start-processing-0" class="edge"></path>
                <path data-id="L-processing-done-1" class="edge"></path>
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
        const nodes = svg.querySelectorAll('g.node');

        const sdxlNode = Array.from(nodes).find(n => n.querySelector('text').textContent === 'SDXLLIFECYCLE');
        const queueNode = Array.from(nodes).find(n => n.querySelector('text').textContent === 'QUEUEMANAGEMENT');

        expect(sdxlNode.dataset.stateId).toBe('SDXLLIFECYCLE');
        expect(queueNode.dataset.stateId).toBe('QUEUEMANAGEMENT');
    });

    it('should enrich edge paths with data-edge-event', () => {
        diagramManager.stateHighlightMap = {};

        // Execute
        diagramManager.enrichSvgWithDataAttributes();

        // Verify
        const svg = diagramManager.container.querySelector('svg');
        const edge1 = svg.querySelector('path[data-id="L-start-processing-0"]');
        const edge2 = svg.querySelector('path[data-id="L-processing-done-1"]');

        expect(edge1.dataset.edgeEvent).toBe('new_job');
        expect(edge2.dataset.edgeEvent).toBe('job_complete');
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
        const nodes = svg.querySelectorAll('g.node');

        const sdxlNode = Array.from(nodes).find(n => n.querySelector('text').textContent === 'SDXLLIFECYCLE');
        const queueNode = Array.from(nodes).find(n => n.querySelector('text').textContent === 'QUEUEMANAGEMENT');

        expect(sdxlNode.dataset.stateId).toBe('SDXLLIFECYCLE');
        expect(queueNode.dataset.stateId).toBeUndefined(); // Not in map
    });

    it('should return enrichedCount > 0 when successful', () => {
        diagramManager.stateHighlightMap = {
            'test': { type: 'composite', target: 'SDXLLIFECYCLE', class: 'activeComposite' }
        };

        const result = diagramManager.enrichSvgWithDataAttributes();

        expect(result).toBe(true);
    });
});

describe('updateStateHighlight', () => {
    let diagramManager;

    beforeEach(() => {
        const container = document.createElement('div');
        const breadcrumb = document.createElement('nav');
        const logger = { log: () => {} };
        diagramManager = new DiagramManager(container, breadcrumb, logger);

        // Create enriched SVG
        container.innerHTML = `
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
                <path data-edge-event="queue_ready" class="edge"></path>
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
        const result = diagramManager.updateStateHighlight('monitoring_sdxl', 'sdxl_job_done');

        expect(result).toBe(true);

        const svg = diagramManager.container.querySelector('svg');
        const edge = svg.querySelector('[data-edge-event="sdxl_job_done"]');

        expect(edge.classList.contains('last-transition-arrow')).toBe(true);

        // Note: Arrow clearing after 2 seconds is tested separately in integration tests
        // as it requires real timers and would slow down unit tests
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

    it('should handle event not found gracefully', () => {
        const result = diagramManager.updateStateHighlight('monitoring_sdxl', 'nonexistent_event');

        // State should still highlight successfully
        expect(result).toBe(true);

        // No error should be thrown
        const svg = diagramManager.container.querySelector('svg');
        const node = svg.querySelector('[data-state-id="SDXLLIFECYCLE"]');
        expect(node.classList.contains('activeComposite')).toBe(true);
    });
});

describe('renderDiagram - Fast vs Slow Path', () => {
    let diagramManager;
    let updateCalls;
    let mermaidCalls;

    beforeEach(() => {
        const container = document.createElement('div');
        const breadcrumb = document.createElement('nav');
        const logger = { log: () => {} };
        diagramManager = new DiagramManager(container, breadcrumb, logger);
        diagramManager.currentDiagram = 'flowchart TD\n  A-->B';
        
        // Track method calls manually
        updateCalls = [];
        mermaidCalls = [];
        
        // Mock updateStateHighlight
        const originalUpdate = diagramManager.updateStateHighlight.bind(diagramManager);
        diagramManager.updateStateHighlight = (...args) => {
            updateCalls.push(args);
            return true; // Default to true, can be overridden
        };
        
        // Mock mermaid
        global.mermaid = {
            run: async (...args) => {
                mermaidCalls.push(args);
            }
        };
    });

    it('should use fast path when enriched and state provided', async () => {
        diagramManager.container.dataset.enriched = 'true';
        diagramManager.stateHighlightMap = { 'test_state': { type: 'state', target: 'test_state', class: 'active' } };

        await diagramManager.renderDiagram('test_state', { event: 'test_event' });

        expect(updateCalls.length).toBe(1);
        expect(updateCalls[0]).toEqual(['test_state', 'test_event']);
        expect(mermaidCalls.length).toBe(0);
    });

    it('should use slow path when updateStateHighlight returns false', async () => {
        diagramManager.container.dataset.enriched = 'true';
        diagramManager.stateHighlightMap = { 'test': {} };
        
        // Override to return false
        diagramManager.updateStateHighlight = (...args) => {
            updateCalls.push(args);
            return false;
        };

        await diagramManager.renderDiagram('test_state');

        expect(updateCalls.length).toBe(1);
        expect(mermaidCalls.length).toBe(1);
    });

    it('should use slow path when no highlight state', async () => {
        diagramManager.container.dataset.enriched = 'true';

        await diagramManager.renderDiagram(null);

        expect(updateCalls.length).toBe(0);
        expect(mermaidCalls.length).toBe(1);
    });
});

describe('loadDiagram - State Clearing', () => {
    let diagramManager;
    let fetchCalls;
    let loadStateCalls;
    let loadTransitionCalls;

    beforeEach(() => {
        const container = document.createElement('div');
        const breadcrumb = document.createElement('nav');
        const logger = { log: () => {} };
        diagramManager = new DiagramManager(container, breadcrumb, logger);

        // Track calls
        fetchCalls = [];
        loadStateCalls = [];
        loadTransitionCalls = [];

        // Mock fetch
        global.fetch = (...args) => {
            fetchCalls.push(args);
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve({
                    mermaid_code: 'flowchart TD\n  A-->B',
                    metadata: { diagrams: { main: {} } }
                })
            });
        };

        // Mock other methods
        diagramManager.updateBreadcrumb = () => {};
        diagramManager.loadMachineState = (...args) => {
            loadStateCalls.push(args);
            return null;
        };
        diagramManager.loadMachineTransition = (...args) => {
            loadTransitionCalls.push(args);
            return null;
        };
        diagramManager.renderDiagram = () => {};
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

describe('Metadata Structure Migration (v1.0.47+)', () => {
    let diagramManager;

    beforeEach(() => {
        const container = document.createElement('div');
        const breadcrumb = document.createElement('nav');
        const logger = { log: () => {} };
        diagramManager = new DiagramManager(container, breadcrumb, logger);
    });

    it('should handle new nested metadata structure in buildStateHighlightMap', () => {
        diagramManager.diagramMetadata = {
            machine_name: 'test-machine',
            diagrams: {
                main: { composites: ['COMPOSITE1'] },
                COMPOSITE1: { states: ['state1', 'state2'] }
            }
        };
        diagramManager.currentDiagramName = 'main';

        const map = diagramManager.buildStateHighlightMap();

        expect(map).not.toBeNull();
        expect(map['state1']).toEqual({
            type: 'composite',
            target: 'COMPOSITE1',
            class: 'activeComposite'
        });
    });

    it('should use new metadata structure in attachCompositeClickHandlers', () => {
        // Setup DOM with realistic structure
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        const composite = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        composite.setAttribute('id', 'flowchart-COMPOSITE1-123'); // Mermaid-style ID
        composite.classList.add('node');
        svg.appendChild(composite);
        diagramManager.container.appendChild(svg);

        // Setup new metadata structure
        diagramManager.diagramMetadata = {
            diagrams: {
                main: { composites: ['COMPOSITE1'] },
                COMPOSITE1: { states: ['state1'] }
            }
        };
        diagramManager.currentDiagramName = 'main';
        diagramManager.selectedMachine = 'test-machine';

        // Track if click handler was added
        let clickAdded = false;
        const originalAddEventListener = composite.addEventListener;
        composite.addEventListener = function(event, handler) {
            if (event === 'click') {
                clickAdded = true;
            }
            return originalAddEventListener.call(this, event, handler);
        };

        // Attach handlers
        diagramManager.attachCompositeClickHandlers();

        // Verify composite is clickable
        expect(clickAdded).toBe(true);
        expect(composite.style.cursor).toBe('pointer');
    });

    it('should handle slow path with new metadata structure', async () => {
        // Setup with new metadata structure
        diagramManager.diagramMetadata = {
            diagrams: {
                SUBDIAGRAM: { states: ['state1', 'state2'] }
            }
        };
        diagramManager.currentDiagramName = 'SUBDIAGRAM';
        diagramManager.currentDiagram = 'flowchart TD\n  state1-->state2';

        // Mock mermaid
        global.mermaid = {
            run: async () => {
                const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                const node = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                node.id = 'flowchart-state1-0';
                svg.appendChild(node);
                diagramManager.container.appendChild(svg);
            }
        };

        // Render with slow path (highlighting a state in subdiagram)
        await diagramManager.renderDiagram('state1');

        // Should complete without errors
        expect(diagramManager.container.querySelector('svg')).not.toBeNull();
    });

    it('should gracefully handle missing metadata with optional chaining', () => {
        diagramManager.diagramMetadata = null;
        diagramManager.currentDiagramName = 'main';

        const map = diagramManager.buildStateHighlightMap();

        expect(map).toBeNull();
    });

    it('should gracefully handle missing current diagram in metadata', () => {
        diagramManager.diagramMetadata = {
            diagrams: {
                main: { composites: [] }
            }
        };
        diagramManager.currentDiagramName = 'NONEXISTENT';

        const map = diagramManager.buildStateHighlightMap();

        expect(map).toBeNull();
    });
});

describe('Composite Click Handler Edge Cases', () => {
    let diagramManager;

    beforeEach(() => {
        const container = document.createElement('div');
        const breadcrumb = document.createElement('nav');
        const logger = { log: () => {} };
        diagramManager = new DiagramManager(container, breadcrumb, logger);
    });

    it('should handle empty composites array', () => {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        diagramManager.container.appendChild(svg);

        diagramManager.diagramMetadata = {
            diagrams: {
                main: { composites: [] }
            }
        };
        diagramManager.currentDiagramName = 'main';

        // Should not throw
        expect(() => diagramManager.attachCompositeClickHandlers()).not.toThrow();
    });

    it('should handle no metadata', () => {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        diagramManager.container.appendChild(svg);

        diagramManager.diagramMetadata = null;
        diagramManager.currentDiagramName = 'main';

        // Should not throw
        expect(() => diagramManager.attachCompositeClickHandlers()).not.toThrow();
    });

    it('should handle composite node not found in SVG', () => {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        diagramManager.container.appendChild(svg);

        diagramManager.diagramMetadata = {
            diagrams: {
                main: { composites: ['MISSING_COMPOSITE'] }
            }
        };
        diagramManager.currentDiagramName = 'main';

        // Should not throw even if composite not in SVG
        expect(() => diagramManager.attachCompositeClickHandlers()).not.toThrow();
    });
});

