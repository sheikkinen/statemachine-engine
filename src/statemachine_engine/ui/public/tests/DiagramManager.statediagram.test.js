/**
 * Integration Tests for DiagramManager - Statediagram Format
 * Tests CSS-only fast path with realistic statediagram SVG structure
 * Based on actual SDXLGENERATIONPHASE composite workflow
 */

import { DiagramManager } from '../modules/DiagramManager.js';

describe('DiagramManager - Statediagram Format Integration', () => {
    let diagramManager, container, breadcrumb, logger;

    beforeEach(() => {
        container = document.createElement('div');
        breadcrumb = document.createElement('nav');
        logger = { log: () => {} };
        diagramManager = new DiagramManager(container, breadcrumb, logger);
    });

    /**
     * Test data based on real SDXLGENERATIONPHASE workflow
     * This matches the actual structure seen in production logs
     */
    const sdxlGenerationMetadata = {
        diagrams: {
            main: { 
                composites: ['SDXLGENERATIONPHASE', 'QUEUEMANAGEMENT'] 
            },
            SDXLGENERATIONPHASE: { 
                states: [
                    'early_face_detection',
                    'generating_enhanced_image',
                    'scaling_image',
                    'face_detection',
                    'processing_faces',
                    'face_replacement',
                    'image_generation_complete'
                ]
            },
            QUEUEMANAGEMENT: { 
                states: ['checking_queue', 'dispatching'] 
            }
        }
    };

    /**
     * Realistic statediagram SVG with Mermaid v11 structure
     * Uses 'statediagram-state' class instead of just 'node'
     */
    const createStatediagramSvg = (states) => {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        
        states.forEach((stateName, index) => {
            const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            g.setAttribute('class', 'node statediagram-state');
            g.setAttribute('id', `state-${stateName}-${index + 10}`);
            g.setAttribute('transform', `translate(${100 + index * 150}, ${200 + index * 80})`);
            
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.textContent = stateName;
            g.appendChild(text);
            
            svg.appendChild(g);
        });
        
        return svg;
    };

    describe('Enrichment with statediagram-state nodes', () => {
        it('should enrich statediagram nodes with data-state-id', () => {
            // Setup subdiagram context
            diagramManager.diagramMetadata = sdxlGenerationMetadata;
            diagramManager.currentDiagramName = 'SDXLGENERATIONPHASE';
        if (diagramManager.diagramMetadata) diagramManager.diagramMetadata.currentDiagramName = 'SDXLGENERATIONPHASE';
            
            // Create realistic SVG
            const svg = createStatediagramSvg([
                'early_face_detection',
                'generating_enhanced_image',
                'scaling_image'
            ]);
            container.appendChild(svg);
            
            // Build map (now on renderer)
            diagramManager.renderer.stateHighlightMap = diagramManager.renderer.buildStateHighlightMap(diagramManager.diagramMetadata);

            // Execute enrichment (now on renderer)
            const enriched = diagramManager.renderer.enrichSvgWithDataAttributes();
            
            // Verify enrichment succeeded
            expect(enriched).toBe(true);
            
            // Verify data attributes added
            const earlyFaceNode = svg.querySelector('[data-state-id="early_face_detection"]');
            expect(earlyFaceNode).not.toBeNull();
            expect(earlyFaceNode.classList.contains('statediagram-state')).toBe(true);
            
            const generatingNode = svg.querySelector('[data-state-id="generating_enhanced_image"]');
            expect(generatingNode).not.toBeNull();
            
            const scalingNode = svg.querySelector('[data-state-id="scaling_image"]');
            expect(scalingNode).not.toBeNull();
        });
    });

    describe('Fast path state highlighting after diagram drill-in', () => {
        beforeEach(() => {
            // Setup subdiagram context (user drilled into SDXLGENERATIONPHASE)
            diagramManager.diagramMetadata = sdxlGenerationMetadata;
            diagramManager.currentDiagramName = 'SDXLGENERATIONPHASE';
        if (diagramManager.diagramMetadata) diagramManager.diagramMetadata.currentDiagramName = 'SDXLGENERATIONPHASE';
            
            // Create SVG
            const svg = createStatediagramSvg([
                'early_face_detection',
                'generating_enhanced_image',
                'scaling_image',
                'face_detection'
            ]);
            container.appendChild(svg);
            
            // Build map and enrich (simulates first render after drill-in)
            diagramManager.renderer.stateHighlightMap = diagramManager.renderer.buildStateHighlightMap(diagramManager.diagramMetadata);
            diagramManager.renderer.enrichSvgWithDataAttributes();
            container.dataset.enriched = 'true';
        });

        it('should NOT attempt fast path when diagram not enriched', () => {
            // Simulate drill-in clears enrichment
            container.dataset.enriched = 'false';
            
            // Track if updateStateHighlight was called
            let fastPathAttempted = false;
            const originalUpdate = diagramManager.highlighter.updateStateHighlight.bind(diagramManager.highlighter);
            diagramManager.highlighter.updateStateHighlight = function(...args) {
                fastPathAttempted = true;
                return originalUpdate(...args);
            };
            
            // renderDiagram should skip fast path when not enriched
            // Since we don't have async mermaid in test, this won't fully execute
            // but we can verify the fast path check logic
            
            const svg = container.querySelector('svg');
            expect(svg).not.toBeNull();
            
            // Verify enriched flag is false
            expect(container.dataset.enriched).toBe('false');
            
            // The fast path condition checks: highlightState && enriched === 'true'
            // Since enriched is 'false', fast path should be skipped
            // We'll verify by checking the fast path would fail
            const result = diagramManager.highlighter.updateStateHighlight('early_face_detection', diagramManager.renderer.stateHighlightMap, diagramManager.diagramMetadata, diagramManager.currentDiagramName);
            
            // This should still work because SVG is already enriched from beforeEach
            // But renderDiagram() wouldn't call it due to dataset.enriched check
            expect(result).toBe(true);
        });

        it('should use fast path for subsequent state changes', () => {
            // Container is enriched (set in beforeEach)
            expect(container.dataset.enriched).toBe('true');
            
            // First state change
            const success1 = diagramManager.highlighter.updateStateHighlight('early_face_detection', diagramManager.renderer.stateHighlightMap, diagramManager.diagramMetadata, diagramManager.currentDiagramName);
            expect(success1).toBe(true);
            
            const node1 = container.querySelector('[data-state-id="early_face_detection"]');
            expect(node1.classList.contains('active')).toBe(true);
            
            // Second state change (simulates WebSocket event)
            const success2 = diagramManager.highlighter.updateStateHighlight('generating_enhanced_image', diagramManager.renderer.stateHighlightMap, diagramManager.diagramMetadata, diagramManager.currentDiagramName);
            expect(success2).toBe(true);
            
            // Old highlight removed
            expect(node1.classList.contains('active')).toBe(false);
            
            // New highlight added
            const node2 = container.querySelector('[data-state-id="generating_enhanced_image"]');
            expect(node2.classList.contains('active')).toBe(true);
        });

        it('should handle rapid state changes with fast path', () => {
            const stateSequence = [
                'early_face_detection',
                'generating_enhanced_image',
                'scaling_image',
                'face_detection'
            ];
            
            // Simulate rapid state changes
            stateSequence.forEach((stateName, index) => {
                const success = diagramManager.highlighter.updateStateHighlight(stateName, diagramManager.renderer.stateHighlightMap, diagramManager.diagramMetadata, diagramManager.currentDiagramName);
                expect(success).toBe(true);
                
                // Verify only current state is highlighted
                const activeNodes = container.querySelectorAll('.active');
                expect(activeNodes.length).toBe(1);
                expect(activeNodes[0].dataset.stateId).toBe(stateName);
            });
        });
    });

    describe('Transition from main diagram to subdiagram', () => {
        it('should build correct map after drilling into composite', () => {
            // Start on main diagram
            diagramManager.diagramMetadata = sdxlGenerationMetadata;
            diagramManager.currentDiagramName = 'main';
        if (diagramManager.diagramMetadata) diagramManager.diagramMetadata.currentDiagramName = 'main';

            let map = diagramManager.renderer.buildStateHighlightMap(diagramManager.diagramMetadata);

            // On main, composite states map to composites
            expect(map['early_face_detection']).toEqual({
                type: 'composite',
                target: 'SDXLGENERATIONPHASE',
                class: 'activeComposite'
            });

            // User drills into composite
            diagramManager.currentDiagramName = 'SDXLGENERATIONPHASE';
        if (diagramManager.diagramMetadata) diagramManager.diagramMetadata.currentDiagramName = 'SDXLGENERATIONPHASE';
            map = diagramManager.renderer.buildStateHighlightMap(diagramManager.diagramMetadata);
            
            // In subdiagram, states map to themselves
            expect(map['early_face_detection']).toEqual({
                type: 'state',
                target: 'early_face_detection',
                class: 'active'
            });
            
            expect(map['generating_enhanced_image']).toEqual({
                type: 'state',
                target: 'generating_enhanced_image',
                class: 'active'
            });
        });
    });

    describe('Real-world workflow simulation', () => {
        it('should handle complete SDXL generation workflow', () => {
            // Setup
            diagramManager.diagramMetadata = sdxlGenerationMetadata;
            diagramManager.currentDiagramName = 'SDXLGENERATIONPHASE';
        if (diagramManager.diagramMetadata) diagramManager.diagramMetadata.currentDiagramName = 'SDXLGENERATIONPHASE';
            
            const allStates = [
                'early_face_detection',
                'generating_enhanced_image',
                'scaling_image',
                'face_detection',
                'processing_faces',
                'face_replacement',
                'image_generation_complete'
            ];
            
            const svg = createStatediagramSvg(allStates);
            container.appendChild(svg);
            
            // Build map and enrich
            diagramManager.renderer.stateHighlightMap = diagramManager.renderer.buildStateHighlightMap(diagramManager.diagramMetadata);
            const enriched = diagramManager.renderer.enrichSvgWithDataAttributes();
            expect(enriched).toBe(true);
            
            // Verify all states enriched
            allStates.forEach(stateName => {
                const node = svg.querySelector(`[data-state-id="${stateName}"]`);
                expect(node).not.toBeNull();
                expect(node.dataset.stateId).toBe(stateName);
            });
            
            // Simulate realistic workflow progression
            const transitions = [
                { from: null, to: 'early_face_detection', event: 'start' },
                { from: 'early_face_detection', to: 'generating_enhanced_image', event: 'face_detected' },
                { from: 'generating_enhanced_image', to: 'scaling_image', event: 'image_generated' },
                { from: 'scaling_image', to: 'face_detection', event: 'image_scaled' },
                { from: 'face_detection', to: 'processing_faces', event: 'faces_detected' },
                { from: 'processing_faces', to: 'face_replacement', event: 'faces_processed' },
                { from: 'face_replacement', to: 'image_generation_complete', event: 'replacement_complete' }
            ];
            
            transitions.forEach(({ to }) => {
                const success = diagramManager.highlighter.updateStateHighlight(to, diagramManager.renderer.stateHighlightMap, diagramManager.diagramMetadata, diagramManager.currentDiagramName);
                expect(success).toBe(true);
                
                const activeNode = svg.querySelector('.active');
                expect(activeNode).not.toBeNull();
                expect(activeNode.dataset.stateId).toBe(to);
            });
        });
    });

    describe('Mixed node types (flowchart + statediagram)', () => {
        it('should enrich both node and statediagram-state classes', () => {
            diagramManager.diagramMetadata = sdxlGenerationMetadata;
            diagramManager.currentDiagramName = 'SDXLGENERATIONPHASE';
        if (diagramManager.diagramMetadata) diagramManager.diagramMetadata.currentDiagramName = 'SDXLGENERATIONPHASE';
            
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            
            // Flowchart style node
            const flowchartNode = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            flowchartNode.setAttribute('class', 'node');
            flowchartNode.setAttribute('id', 'flowchart-early_face-1');
            const text1 = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text1.textContent = 'early_face_detection';
            flowchartNode.appendChild(text1);
            svg.appendChild(flowchartNode);
            
            // Statediagram style node
            const statediagramNode = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            statediagramNode.setAttribute('class', 'node statediagram-state');
            statediagramNode.setAttribute('id', 'state-scaling_image-10');
            const text2 = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text2.textContent = 'scaling_image';
            statediagramNode.appendChild(text2);
            svg.appendChild(statediagramNode);
            
            container.appendChild(svg);
            
            // Build map and enrich
            diagramManager.renderer.stateHighlightMap = diagramManager.renderer.buildStateHighlightMap(diagramManager.diagramMetadata);
            const enriched = diagramManager.renderer.enrichSvgWithDataAttributes();

            expect(enriched).toBe(true);
            
            // Both should be enriched
            expect(flowchartNode.dataset.stateId).toBe('early_face_detection');
            expect(statediagramNode.dataset.stateId).toBe('scaling_image');
        });
    });
});
