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
        const logger = { log: jest.fn() };
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
        expect(Object.keys(map).length).toBe(4);

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

        expect(map).toEqual({});
    });
});

describe('enrichSvgWithDataAttributes', () => {
    let diagramManager;

    beforeEach(() => {
        const container = document.createElement('div');
        const breadcrumb = document.createElement('nav');
        const logger = { log: jest.fn() };
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
        const logger = { log: jest.fn() };
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

    beforeEach(() => {
        const container = document.createElement('div');
        const breadcrumb = document.createElement('nav');
        const logger = { log: jest.fn() };
        diagramManager = new DiagramManager(container, breadcrumb, logger);
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

describe('loadDiagram - State Clearing', () => {
    let diagramManager;

    beforeEach(() => {
        const container = document.createElement('div');
        const breadcrumb = document.createElement('nav');
        const logger = { log: jest.fn() };
        diagramManager = new DiagramManager(container, breadcrumb, logger);

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
        diagramManager.renderDiagram = jest.fn();
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
