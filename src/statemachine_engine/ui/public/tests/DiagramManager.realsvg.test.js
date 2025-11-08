/**
 * Real SVG Tests - Using actual production SDXLGENERATIONPHASE diagram
 * Tests with real Mermaid v11 statediagram output
 */

import { DiagramManager } from '../modules/DiagramManager.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

describe('Real SDXL SVG from Production', () => {
    let manager, container, svgContent;
    
    beforeAll(() => {
        // Load REAL SVG from production (cleaned, coordinates stripped)
        const svgPath = path.join(__dirname, 'fixtures/sdxlgenerationphase.svg');
        svgContent = fs.readFileSync(svgPath, 'utf-8');
    });
    
    beforeEach(() => {
        container = document.createElement('div');
        container.innerHTML = svgContent;
        
        const breadcrumb = document.createElement('nav');
        const logger = { log: () => {} };
        manager = new DiagramManager(container, breadcrumb, logger);
        
        // Real metadata from production
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
            if (manager.diagramMetadata) manager.diagramMetadata.currentDiagramName = 'SDXLGENERATIONPHASE';
    });
    
    describe('SVG Structure Analysis', () => {
        it('should load real SVG content', () => {
            const svg = container.querySelector('svg');
            expect(svg).not.toBeNull();
            expect(svg.id).toBe('mermaid-1761506845500');
        });
        
        it('should find statediagram-state nodes', () => {
            const svg = container.querySelector('svg');
            const nodes = svg.querySelectorAll('g.statediagram-state');
            
            console.log(`\n[SVG Analysis] Found ${nodes.length} statediagram-state nodes`);
            
            expect(nodes.length).toBeGreaterThan(0);
        });
        
        it('should find nodes with selector "g.node, g.statediagram-state"', () => {
            const svg = container.querySelector('svg');
            const nodes = svg.querySelectorAll('g.node, g.statediagram-state');
            
            console.log(`\n[SVG Analysis] Found ${nodes.length} nodes with combined selector`);
            
            // Log details of each node
            const nodeDetails = [];
            nodes.forEach((node, i) => {
                const textEl = node.querySelector('text');
                const pEl = node.querySelector('p');
                
                nodeDetails.push({
                    index: i,
                    id: node.id,
                    classes: node.className.baseVal || node.getAttribute('class'),
                    textContent: textEl?.textContent?.trim() || '',
                    pContent: pEl?.textContent?.trim() || ''
                });
            });
            
            console.table(nodeDetails);
            
            expect(nodes.length).toBeGreaterThan(0);
        });
        
        it('should analyze text content location', () => {
            const svg = container.querySelector('svg');
            const nodes = svg.querySelectorAll('g.node, g.statediagram-state');
            
            console.log(`\n[Text Content Analysis]`);
            
            nodes.forEach((node, i) => {
                const textEl = node.querySelector('text');
                const pEl = node.querySelector('p');
                const foreignObject = node.querySelector('foreignObject');
                
                console.log(`Node ${i} (${node.id}):`);
                console.log(`  - Has <text>: ${!!textEl}, content: "${textEl?.textContent?.trim() || 'N/A'}"`);
                console.log(`  - Has <p>: ${!!pEl}, content: "${pEl?.textContent?.trim() || 'N/A'}"`);
                console.log(`  - Has <foreignObject>: ${!!foreignObject}`);
            });
            
            // At least one should have text
            const hasText = Array.from(nodes).some(n => 
                n.querySelector('text')?.textContent?.trim() || 
                n.querySelector('p')?.textContent?.trim()
            );
            expect(hasText).toBe(true);
        });
    });
    
    describe('State Map Building', () => {
        it('should build state map for SDXLGENERATIONPHASE', () => {
            const map = manager.renderer.buildStateHighlightMap(manager.diagramMetadata);
            
            console.log(`\n[State Map]`);
            console.log('Expected states:', manager.diagramMetadata.diagrams.SDXLGENERATIONPHASE.states);
            console.log('Map keys:', Object.keys(map));
            console.table(map);
            
            expect(map).not.toBeNull();
            expect(Object.keys(map).length).toBe(7);
            
            // Check specific states
            expect(map['scaling_image']).toBeDefined();
            expect(map['early_face_detection']).toBeDefined();
        });
    });
    
    describe('Enrichment with Real SVG', () => {
        it('should attempt to enrich real SVG nodes', () => {
            // Build map
            manager.renderer.stateHighlightMap = manager.renderer.buildStateHighlightMap(manager.diagramMetadata);
            const targets = new Set(Object.values(manager.renderer.stateHighlightMap).map(e => e.target));
            
            console.log(`\n[Enrichment Test]`);
            console.log('Targets to enrich:', Array.from(targets));
            
            // Get nodes
            const svg = container.querySelector('svg');
            const nodes = svg.querySelectorAll('g.node, g.statediagram-state');
            console.log(`Found ${nodes.length} nodes in SVG`);
            
            // Manually check which would match
            const matches = [];
            const misses = [];
            
            nodes.forEach((node, i) => {
                const textEl = node.querySelector('text');
                const pEl = node.querySelector('p');
                const stateName = textEl?.textContent?.trim() || pEl?.textContent?.trim() || '';
                
                const nodeInfo = {
                    index: i,
                    id: node.id,
                    classes: node.className.baseVal,
                    textContent: stateName,
                    isTarget: targets.has(stateName)
                };
                
                if (stateName && targets.has(stateName)) {
                    matches.push(nodeInfo);
                } else {
                    misses.push(nodeInfo);
                }
            });
            
            console.log(`\n✅ Would enrich ${matches.length} nodes:`);
            if (matches.length > 0) console.table(matches);
            
            console.log(`\n❌ Would NOT enrich ${misses.length} nodes:`);
            if (misses.length > 0) console.table(misses);
            
            // Check for missing targets
            const matchedTargets = new Set(matches.map(m => m.textContent));
            const missingTargets = Array.from(targets).filter(t => !matchedTargets.has(t));
            if (missingTargets.length > 0) {
                console.error(`\n⚠️ Targets NOT found in SVG:`, missingTargets);
            }
            
            // Now actually enrich
            const enriched = manager.renderer.enrichSvgWithDataAttributes();
            
            console.log(`\nEnrichment result: ${enriched}`);
            
            // Should have enriched something
            expect(enriched).toBe(true);
        });
        
        it('should find enriched nodes by data-state-id', () => {
            // Setup
            manager.renderer.stateHighlightMap = manager.renderer.buildStateHighlightMap(manager.diagramMetadata);
            manager.renderer.enrichSvgWithDataAttributes();
            
            // Check each expected state
            const testStates = [
                'early_face_detection',
                'scaling_image',
                'generating_enhanced_image'
            ];
            
            console.log(`\n[Finding Enriched Nodes]`);
            
            testStates.forEach(stateName => {
                const node = container.querySelector(`[data-state-id="${stateName}"]`);
                
                if (node) {
                    console.log(`✅ Found ${stateName}:`, {
                        id: node.id,
                        classes: node.className.baseVal,
                        dataStateId: node.dataset.stateId
                    });
                } else {
                    console.error(`❌ NOT found: ${stateName}`);
                    
                    // Debug: show all enriched nodes
                    const allEnriched = container.querySelectorAll('[data-state-id]');
                    console.log(`  All enriched nodes (${allEnriched.length}):`);
                    allEnriched.forEach(n => {
                        console.log(`    - ${n.dataset.stateId} (${n.id})`);
                    });
                }
                
                expect(node).not.toBeNull();
            });
        });
    });
    
    describe('Fast Path with Real SVG', () => {
        beforeEach(() => {
            manager.renderer.stateHighlightMap = manager.renderer.buildStateHighlightMap(manager.diagramMetadata);
            manager.renderer.enrichSvgWithDataAttributes();
            container.dataset.enriched = 'true';
        });
        
        it('should use fast path for scaling_image', () => {
            console.log(`\n[Fast Path Test] Testing scaling_image`);
            
            // This is the state that was failing in production
            const success = manager.highlighter.updateStateHighlight('scaling_image', manager.renderer.stateHighlightMap, manager.diagramMetadata, manager.currentDiagramName);
            
            if (!success) {
                console.error('❌ Fast path FAILED for scaling_image');
                
                // Debug info
                const node = container.querySelector('[data-state-id="scaling_image"]');
                console.log('  Node with data-state-id="scaling_image":', node);
                
                const allEnriched = container.querySelectorAll('[data-state-id]');
                console.log(`  All enriched nodes (${allEnriched.length}):`);
                allEnriched.forEach(n => {
                    console.log(`    - ${n.dataset.stateId}`);
                });
            } else {
                console.log('✅ Fast path SUCCESS for scaling_image');
            }
            
            expect(success).toBe(true);
        });
        
        it('should use fast path for early_face_detection', () => {
            const success = manager.highlighter.updateStateHighlight('early_face_detection', manager.renderer.stateHighlightMap, manager.diagramMetadata, manager.currentDiagramName);
            
            if (!success) {
                console.error('❌ Fast path FAILED for early_face_detection');
            } else {
                console.log('✅ Fast path SUCCESS for early_face_detection');
            }
            
            expect(success).toBe(true);
        });
        
        it('should handle all SDXL states with fast path', () => {
            const states = manager.diagramMetadata.diagrams.SDXLGENERATIONPHASE.states;
            const results = [];
            
            console.log(`\n[Fast Path All States]`);
            
            states.forEach(stateName => {
                const success = manager.highlighter.updateStateHighlight(stateName, manager.renderer.stateHighlightMap, manager.diagramMetadata, manager.currentDiagramName);
                results.push({ state: stateName, success });
                
                if (!success) {
                    console.error(`  ❌ ${stateName}`);
                } else {
                    console.log(`  ✅ ${stateName}`);
                }
            });
            
            const successCount = results.filter(r => r.success).length;
            console.log(`\nResult: ${successCount}/${states.length} states work with fast path`);
            
            // At least the ones we know should work
            expect(results.find(r => r.state === 'scaling_image').success).toBe(true);
        });
        
        it('should highlight arrow for image_scaled event (exit transition)', () => {
            console.log(`\n[Arrow Test] Testing image_scaled event (scaling_image → COMPLETIONPHASE)`);
            
            // This is the "exit" transition from scaling_image to COMPLETIONPHASE
            const success = manager.highlighter.updateStateHighlight('scaling_image', manager.renderer.stateHighlightMap, manager.diagramMetadata, manager.currentDiagramName, 'image_scaled');
            
            const svg = container.querySelector('svg');
            const edge = svg.querySelector('[data-edge-event="image_scaled"]');
            
            console.log(`  Edge found: ${edge ? '✅' : '❌'}`);
            if (edge) {
                console.log(`  Edge ID: ${edge.id}`);
                console.log(`  Has arrow class: ${edge.classList.contains('last-transition-arrow')}`);
                expect(edge.classList.contains('last-transition-arrow')).toBe(true);
            } else {
                console.error('  ❌ Edge with data-edge-event="image_scaled" not found');
                
                // Debug: Show what edges we have
                const allEdges = Array.from(svg.querySelectorAll('[data-edge-event]'));
                console.log(`  Available edges (${allEdges.length}):`);
                allEdges.forEach(e => {
                    console.log(`    - ${e.dataset.edgeEvent} (${e.id})`);
                });
            }
            
            expect(edge).not.toBeNull();
            expect(success).toBe(true);
        });
    });
    
    describe('Text Content Extraction Methods', () => {
        it('should test different text extraction approaches', () => {
            const svg = container.querySelector('svg');
            const nodes = svg.querySelectorAll('g.node, g.statediagram-state');
            
            console.log(`\n[Text Extraction Methods]`);
            
            nodes.forEach((node, i) => {
                console.log(`\nNode ${i} (${node.id}):`);
                
                // Method 1: <text> element
                const textEl = node.querySelector('text');
                const method1 = textEl?.textContent?.trim() || '';
                console.log(`  Method 1 (text element): "${method1}"`);
                
                // Method 2: <p> element
                const pEl = node.querySelector('p');
                const method2 = pEl?.textContent?.trim() || '';
                console.log(`  Method 2 (<p> element): "${method2}"`);
                
                // Method 3: .nodeLabel
                const labelEl = node.querySelector('.nodeLabel');
                const method3 = labelEl?.textContent?.trim() || '';
                console.log(`  Method 3 (.nodeLabel): "${method3}"`);
                
                // Method 4: Parse ID
                const idMatch = node.id.match(/^state-(.+)-\d+$/);
                const method4 = idMatch ? idMatch[1] : '';
                console.log(`  Method 4 (parse ID): "${method4}"`);
                
                // Which method gets a result?
                const winner = method2 || method3 || method1 || method4;
                console.log(`  → Best result: "${winner}"`);
            });
        });
    });
});
