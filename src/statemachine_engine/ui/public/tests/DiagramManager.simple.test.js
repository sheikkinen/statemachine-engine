/**
 * Simplified Unit Tests for DiagramManager - CSS-Only Updates
 * Basic tests without complex mocking - focus on core logic
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

    test('should build map for main diagram with composites', () => {
        // Setup
        diagramManager.diagramMetadata = {
            diagrams: {
                main: { composites: ['SDXLLIFECYCLE', 'QUEUEMANAGEMENT'] },
                SDXLLIFECYCLE: { states: ['monitoring_sdxl', 'completing_sdxl'] },
                QUEUEMANAGEMENT: { states: ['checking_queue', 'dispatching'] }
            }
        };
        diagramManager.currentDiagramName = 'main';
        if (diagramManager.diagramMetadata) diagramManager.diagramMetadata.currentDiagramName = 'main';

        // Execute
        const map = diagramManager.renderer.buildStateHighlightMap(diagramManager.diagramMetadata);

        // Verify
        expect(map).not.toBeNull();
        expect(Object.keys(map).length).toBe(6); // 2 composites + 4 substates
        
        // Composites should map to themselves
        expect(map['SDXLLIFECYCLE'].type).toBe('composite');
        expect(map['SDXLLIFECYCLE'].target).toBe('SDXLLIFECYCLE');
        expect(map['SDXLLIFECYCLE'].class).toBe('activeComposite');
        
        expect(map['QUEUEMANAGEMENT'].type).toBe('composite');
        expect(map['QUEUEMANAGEMENT'].target).toBe('QUEUEMANAGEMENT');
        expect(map['QUEUEMANAGEMENT'].class).toBe('activeComposite');
        
        // Substates should map to their parent composite
        expect(map['monitoring_sdxl'].type).toBe('composite');
        expect(map['monitoring_sdxl'].target).toBe('SDXLLIFECYCLE');
        expect(map['monitoring_sdxl'].class).toBe('activeComposite');
    });

    test('should build map for subdiagram with direct states', () => {
        // Setup
        diagramManager.diagramMetadata = {
            diagrams: {
                main: { composites: ['SDXLLIFECYCLE'] },
                SDXLLIFECYCLE: { states: ['monitoring_sdxl', 'completing_sdxl'] }
            }
        };
        diagramManager.currentDiagramName = 'SDXLLIFECYCLE';
        if (diagramManager.diagramMetadata) diagramManager.diagramMetadata.currentDiagramName = 'SDXLLIFECYCLE';

        // Execute
        const map = diagramManager.renderer.buildStateHighlightMap(diagramManager.diagramMetadata);

        // Verify
        expect(map).not.toBeNull();
        expect(Object.keys(map).length).toBe(2);
        expect(map['monitoring_sdxl'].type).toBe('state');
        expect(map['monitoring_sdxl'].target).toBe('monitoring_sdxl');
        expect(map['monitoring_sdxl'].class).toBe('active');
    });

    test('should return null when metadata missing', () => {
        diagramManager.diagramMetadata = null;
        diagramManager.currentDiagramName = 'main';
        if (diagramManager.diagramMetadata) diagramManager.diagramMetadata.currentDiagramName = 'main';

        const map = diagramManager.renderer.buildStateHighlightMap(diagramManager.diagramMetadata);

        expect(map).toBeNull();
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
                </g>
                <path data-id="L-start-processing-0" class="edge"></path>
            </svg>
        `;
    });

    test('should enrich state nodes with data-state-id', () => {
        // Setup map
        diagramManager.renderer.stateHighlightMap = {
            'monitoring_sdxl': { type: 'composite', target: 'SDXLLIFECYCLE', class: 'activeComposite' },
            'checking_queue': { type: 'composite', target: 'QUEUEMANAGEMENT', class: 'activeComposite' }
        };

        // Execute
        const result = diagramManager.renderer.enrichSvgWithDataAttributes();

        // Verify
        expect(result).toBe(true);

        const svg = diagramManager.container.querySelector('svg');
        const nodes = svg.querySelectorAll('g.node');

        const sdxlNode = Array.from(nodes).find(n => n.querySelector('text').textContent === 'SDXLLIFECYCLE');
        const queueNode = Array.from(nodes).find(n => n.querySelector('text').textContent === 'QUEUEMANAGEMENT');

        expect(sdxlNode.dataset.stateId).toBe('SDXLLIFECYCLE');
        expect(queueNode.dataset.stateId).toBe('QUEUEMANAGEMENT');
    });

    test('should return false when no SVG', () => {
        diagramManager.container.innerHTML = '';
        diagramManager.renderer.stateHighlightMap = {};

        const result = diagramManager.renderer.enrichSvgWithDataAttributes();

        expect(result).toBe(false);
    });

    test('should return false when no stateHighlightMap', () => {
        diagramManager.renderer.stateHighlightMap = null;

        const result = diagramManager.renderer.enrichSvgWithDataAttributes();

        expect(result).toBe(false);
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
            </svg>
        `;

        // Setup map
        diagramManager.renderer.stateHighlightMap = {
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

    test('should highlight composite node for state in map', () => {
        const result = diagramManager.highlighter.updateStateHighlight('monitoring_sdxl', diagramManager.renderer.stateHighlightMap, diagramManager.diagramMetadata, diagramManager.currentDiagramName);

        expect(result).toBe(true);

        const svg = diagramManager.container.querySelector('svg');
        const node = svg.querySelector('[data-state-id="SDXLLIFECYCLE"]');

        expect(node.classList.contains('activeComposite')).toBe(true);
    });

    test('should remove old highlights before adding new', () => {
        // First highlight
        diagramManager.highlighter.updateStateHighlight('monitoring_sdxl', diagramManager.renderer.stateHighlightMap, diagramManager.diagramMetadata, diagramManager.currentDiagramName);

        const svg = diagramManager.container.querySelector('svg');
        const sdxlNode = svg.querySelector('[data-state-id="SDXLLIFECYCLE"]');
        expect(sdxlNode.classList.contains('activeComposite')).toBe(true);

        // Second highlight
        diagramManager.highlighter.updateStateHighlight('checking_queue', diagramManager.renderer.stateHighlightMap, diagramManager.diagramMetadata, diagramManager.currentDiagramName);

        // Old highlight removed
        expect(sdxlNode.classList.contains('activeComposite')).toBe(false);

        // New highlight added
        const queueNode = svg.querySelector('[data-state-id="QUEUEMANAGEMENT"]');
        expect(queueNode.classList.contains('activeComposite')).toBe(true);
    });

    test('should return false when state not in map', () => {
        const result = diagramManager.highlighter.updateStateHighlight('unknown_state', diagramManager.renderer.stateHighlightMap, diagramManager.diagramMetadata, diagramManager.currentDiagramName);

        expect(result).toBe(false);
    });

    test('should return false when no SVG', () => {
        diagramManager.container.innerHTML = '';

        const result = diagramManager.highlighter.updateStateHighlight('monitoring_sdxl', diagramManager.renderer.stateHighlightMap, diagramManager.diagramMetadata, diagramManager.currentDiagramName);

        expect(result).toBe(false);
    });

    test('should return false when no stateHighlightMap', () => {
        diagramManager.renderer.stateHighlightMap = null;

        const result = diagramManager.highlighter.updateStateHighlight('monitoring_sdxl', diagramManager.renderer.stateHighlightMap, diagramManager.diagramMetadata, diagramManager.currentDiagramName);

        expect(result).toBe(false);
    });
});

console.log('✅ All tests configured and ready to run!');
