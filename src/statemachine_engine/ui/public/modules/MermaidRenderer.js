/**
 * MermaidRenderer - Handles Mermaid diagram rendering and SVG enrichment
 * 
 * Responsibilities:
 * - Render Mermaid code to SVG
 * - Build state highlight lookup maps
 * - Enrich SVG with data attributes for fast queries
 * - Attach composite click handlers
 * 
 * Version: v1.0.54
 */

export class MermaidRenderer {
    constructor(container, logger) {
        this.container = container;
        this.logger = logger;
        this.stateHighlightMap = null;
    }

    /**
     * Render Mermaid diagram to SVG
     * @param {string} mermaidCode - Mermaid diagram code
     * @param {Object} metadata - Diagram metadata
     * @returns {Promise<void>}
     */
    async render(mermaidCode, metadata) {
        if (!mermaidCode) return;

        try {
            this.container.classList.add('redrawing');
            this.container.innerHTML = '';

            const { svg } = await mermaid.render('diagram-svg', mermaidCode);
            this.container.innerHTML = svg;

            // Build highlight map and enrich SVG
            this.stateHighlightMap = this.buildStateHighlightMap(metadata);
            const enriched = this.enrichSvgWithDataAttributes();

            if (enriched && this.stateHighlightMap) {
                this.container.dataset.enriched = 'true';
                console.log('[Render] ✓ Fast path enabled');
            } else {
                this.container.dataset.enriched = 'false';
                console.log('[Render] ⚠️  Fast path disabled - fallback to full render');
            }

            this.container.classList.remove('redrawing');
            console.log('[Render] ✓ Full render (~150ms)');

        } catch (error) {
            console.error('Error rendering diagram:', error);
            this.logger.log('error', `Diagram rendering failed: ${error.message}`);
            this.container.classList.remove('redrawing');
            this.container.dataset.enriched = 'false';
            throw error;
        }
    }

    /**
     * Build state highlight lookup map from metadata
     * Pre-computes what to highlight for each state (composite vs individual)
     *
     * @param {Object} metadata - Diagram metadata
     * @returns {Object|null} Map of state → {type, target, class} or null if no metadata
     */
    buildStateHighlightMap(metadata) {
        const map = {};

        if (!metadata?.diagrams) {
            console.warn('[Map] No metadata - will fallback to full render');
            return null;
        }

        const currentDiagramName = metadata.currentDiagramName || 'main';
        const currentDiagram = metadata.diagrams[currentDiagramName];
        
        if (!currentDiagram) {
            console.warn(`[Map] No metadata for ${currentDiagramName}`);
            return null;
        }

        // Main diagram: Map states → composites
        if (currentDiagramName === 'main') {
            console.log(`[Map] Building map for main diagram`);
            console.log(`[Map] Available diagrams:`, Object.keys(metadata.diagrams));
            
            for (const [compositeName, compositeData] of Object.entries(metadata.diagrams)) {
                if (compositeName === 'main') continue;

                console.log(`[Map] Checking composite "${compositeName}":`, compositeData);

                // Add the composite itself to the map
                map[compositeName] = {
                    type: 'composite',
                    target: compositeName,
                    class: 'activeComposite'
                };

                // Add all substates → composite mapping
                if (compositeData.states && Array.isArray(compositeData.states)) {
                    console.log(`[Map] ${compositeName}: ${compositeData.states.length} states`, compositeData.states);
                    for (const stateName of compositeData.states) {
                        map[stateName] = {
                            type: 'composite',
                            target: compositeName,
                            class: 'activeComposite'
                        };
                    }
                } else {
                    console.warn(`[Map] ${compositeName}: No states array found`);
                }
            }
            console.log(`[Map] Main diagram: ${Object.keys(map).length} states → composites`);
            console.log(`[Map] Full map:`, map);
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
                console.log(`[Map] ${currentDiagramName}: ${Object.keys(map).length} states`);
            }
        }

        return map;
    }

    /**
     * Enrich SVG with data attributes for fast DOM queries
     * Adds data-state-id to state nodes and data-edge-event to transition arrows
     *
     * @returns {boolean} True if enrichment succeeded, false otherwise
     */
    enrichSvgWithDataAttributes() {
        const svg = this.container.querySelector('svg');
        if (!svg || !this.stateHighlightMap) return false;

        let enrichedCount = 0;
        const targets = new Set(Object.values(this.stateHighlightMap).map(e => e.target));

        // Enrich state nodes (supports both flowchart and statediagram)
        const stateNodes = svg.querySelectorAll('g.node, g.statediagram-state, g.statediagram-cluster');
        stateNodes.forEach(node => {
            const textEl = node.querySelector('text');
            const pEl = node.querySelector('p');
            const stateName = (pEl?.textContent?.trim() || textEl?.textContent?.trim() || '');

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

    /**
     * Attach click handlers to composite states for navigation
     * @param {Object} metadata - Diagram metadata
     * @param {string} currentDiagramName - Current diagram name
     * @param {Function} onCompositeClick - Callback(compositeName)
     */
    attachCompositeClickHandlers(metadata, currentDiagramName, onCompositeClick) {
        if (!metadata) {
            console.log('[Composite] No metadata available');
            return;
        }

        const svgEl = this.container.querySelector('svg');
        if (!svgEl) {
            console.log('[Composite] No SVG element found');
            return;
        }
        
        const currentDiagram = metadata.diagrams?.[currentDiagramName];
        const composites = currentDiagram?.composites || [];
        console.log('[Composite] Looking for composites:', composites);
        
        composites.forEach(compositeName => {
            const selectors = [
                `[id*="${compositeName}"]`,
                `g[id*="${compositeName}"]`,
            ];
            
            let compositeNode = null;
            for (const selector of selectors) {
                compositeNode = svgEl.querySelector(selector);
                if (compositeNode) {
                    console.log(`[Composite] ✓ Found ${compositeName} with selector: ${selector}`);
                    break;
                }
            }
            
            // Fallback: try finding by text content
            if (!compositeNode) {
                const textNodes = Array.from(svgEl.querySelectorAll('text'));
                const matchingText = textNodes.find(node => 
                    node.textContent.trim() === compositeName
                );
                
                if (matchingText) {
                    compositeNode = matchingText.closest('g.node');
                    if (compositeNode) {
                        console.log(`[Composite] ✓ Found ${compositeName} by text matching`);
                    }
                }
            }
            
            if (compositeNode) {
                compositeNode.style.cursor = 'pointer';
                compositeNode.addEventListener('click', (e) => {
                    console.log(`[Composite] 🖱️  Clicked: ${compositeName}`);
                    e.stopPropagation();
                    onCompositeClick(compositeName);
                });
                
                // Visual feedback
                compositeNode.addEventListener('mouseenter', () => {
                    compositeNode.style.opacity = '0.8';
                });
                compositeNode.addEventListener('mouseleave', () => {
                    compositeNode.style.opacity = '1';
                });
            } else {
                console.warn(`[Composite] ✗ Could not find node for: ${compositeName}`);
            }
        });
    }

    /**
     * Get the current state highlight map
     * @returns {Object|null}
     */
    getStateHighlightMap() {
        return this.stateHighlightMap;
    }

    /**
     * Clear the fast path state
     */
    clearFastPath() {
        this.container.dataset.enriched = 'false';
        this.stateHighlightMap = null;
    }
}
