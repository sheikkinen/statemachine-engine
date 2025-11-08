/**
 * EventHighlighter - Handles state highlighting and transition animations
 * 
 * Responsibilities:
 * - CSS-only state highlighting (fast path)
 * - Transition arrow animations
 * - Edge finding and highlighting
 * - Composite state resolution
 * 
 * Version: v1.0.54
 */

export class EventHighlighter {
    constructor(container, logger) {
        this.container = container;
        this.logger = logger;
        this.currentHighlightedEdge = null;
        this.highlightTimestamp = null;
    }

    /**
     * Update state highlight using CSS-only approach (FAST PATH)
     * 
     * @param {string} stateName - State to highlight
     * @param {Object} stateHighlightMap - Pre-built highlight map
     * @param {Object} metadata - Diagram metadata
     * @param {string} currentDiagramName - Current diagram name
     * @param {string} eventName - Optional event for transition arrow
     * @returns {boolean} True if CSS-only update succeeded, false to trigger fallback
     */
    updateStateHighlight(stateName, stateHighlightMap, metadata, currentDiagramName, eventName = null) {
        const svg = this.container.querySelector('svg');
        if (!svg) return false;

        if (!stateHighlightMap) {
            console.warn('[CSS-only] No state map - fallback');
            return false;
        }

        // Lookup what to highlight
        let entry = stateHighlightMap[stateName];
        if (!entry) {
            console.warn(`[CSS-only] State "${stateName}" not in map - checking if it's in a composite`);
            
            // Check if this state is in any composite
            if (metadata?.diagrams) {
                for (const [compositeName, compositeData] of Object.entries(metadata.diagrams)) {
                    if (compositeName === 'main') continue;
                    
                    if (compositeData.states && compositeData.states.includes(stateName)) {
                        console.log(`[CSS-only] ✓ Found "${stateName}" in composite "${compositeName}"`);
                        
                        if (currentDiagramName === 'main') {
                            entry = {
                                type: 'composite',
                                target: compositeName,
                                class: 'activeComposite'
                            };
                        } else {
                            const compositeNode = svg?.querySelector(`[data-state-id="${compositeName}"]`);
                            if (compositeNode) {
                                console.log(`[CSS-only] ✓ Composite node "${compositeName}" exists on current diagram`);
                                entry = {
                                    type: 'composite',
                                    target: compositeName,
                                    class: 'activeComposite'
                                };
                            } else {
                                console.log(`[CSS-only] Composite node "${compositeName}" not found on current diagram`);
                                return false;
                            }
                        }
                        
                        // Cache for next time
                        stateHighlightMap[stateName] = entry;
                        break;
                    }
                }
            }
            
            if (!entry) {
                console.warn(`[CSS-only] State "${stateName}" not found in any composite - fallback`);
                return false;
            }
        }
        
        console.log(`[CSS-only] Map lookup for "${stateName}":`, entry);

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
        console.log(`[CSS-only] ✓ ${entry.type}: ${entry.target} (~1ms)`);

        // Highlight arrow
        if (eventName) {
            this.highlightArrow(eventName);
        }

        return true;
    }

    /**
     * Highlight transition arrow by event name
     * @param {string} eventName - Event name to highlight
     */
    highlightArrow(eventName) {
        const svg = this.container.querySelector('svg');
        if (!svg) return;

        // Clear existing highlights
        svg.querySelectorAll('.last-transition-arrow').forEach(el => {
            el.classList.remove('last-transition-arrow');
        });

        const edge = svg.querySelector(`[data-edge-event="${eventName}"]`);
        if (edge) {
            edge.classList.add('last-transition-arrow');
            console.log(`[CSS-only] ✓ Arrow: ${eventName}`);

            setTimeout(() => {
                edge.classList.remove('last-transition-arrow');
            }, 2000);
        } else {
            console.warn(`[CSS-only] ✗ Arrow not found for event: "${eventName}"`);
        }
    }

    /**
     * Highlight transition arrow by transition object (with timestamp tracking)
     * @param {Object} transition - Transition object {from, to, event}
     */
    highlightTransitionArrow(transition) {
        const timestamp = Date.now();
        console.log(`[Arrow Highlight] ${timestamp} - Highlighting transition:`, transition);
        
        const svg = this.container.querySelector('svg');
        if (!svg) return;

        this.clearArrowHighlights();

        const eventTrigger = transition.event;
        const fromState = transition.from;
        const toState = transition.to;
        
        console.log(`[Arrow Highlight] ${timestamp} - Event trigger: "${eventTrigger}" (${fromState} → ${toState})`);
        
        if (eventTrigger && eventTrigger !== 'unknown') {
            const edge = this.findEdgeByLabel(svg, eventTrigger);
            
            if (edge) {
                console.log(`[Arrow Highlight] ${timestamp} - ✓ Found edge by label for "${eventTrigger}"`);
                edge.classList.add('last-transition-arrow');
                
                this.currentHighlightedEdge = edge;
                this.highlightTimestamp = timestamp;
                
                setTimeout(() => {
                    if (edge === this.currentHighlightedEdge && this.highlightTimestamp === timestamp) {
                        console.log(`[Arrow Highlight] ${timestamp} - Clearing highlight after timeout`);
                        edge.classList.remove('last-transition-arrow');
                        this.currentHighlightedEdge = null;
                        this.highlightTimestamp = null;
                    } else {
                        console.log(`[Arrow Highlight] ${timestamp} - Skipping clear - highlight was replaced`);
                    }
                }, 2000);
                return;
            } else {
                console.log(`[Arrow Highlight] ${timestamp} - ✗ Could not find edge by label for "${eventTrigger}"`);
            }
        } else {
            console.log(`[Arrow Highlight] ${timestamp} - No valid event trigger found`);
        }
        
        console.log(`[Arrow Highlight] ${timestamp} - ✗ Skipping animation - no specific edge found`);
    }

    /**
     * Clear all arrow highlights
     */
    clearArrowHighlights() {
        const svg = this.container.querySelector('svg');
        if (!svg) return;

        const highlightedEdges = svg.querySelectorAll('.last-transition-arrow');
        if (highlightedEdges.length > 0) {
            console.log(`[Clear Highlights] Clearing ${highlightedEdges.length} existing highlights`);
            highlightedEdges.forEach(edge => {
                edge.classList.remove('last-transition-arrow');
            });
        }
        
        this.currentHighlightedEdge = null;
        this.highlightTimestamp = null;
    }

    /**
     * Find edge path by label text
     * @param {SVGElement} svg - SVG element
     * @param {string} eventTrigger - Event name to find
     * @returns {Element|null} Edge path element or null
     */
    findEdgeByLabel(svg, eventTrigger) {
        const edgeLabels = svg.querySelectorAll('g.edgeLabels g.label');
        
        for (const label of edgeLabels) {
            const labelText = label.textContent || '';
            if (labelText.includes(eventTrigger)) {
                const dataId = label.getAttribute('data-id');
                if (dataId) {
                    console.log(`[Arrow Highlight] Found label with event "${eventTrigger}", data-id: "${dataId}"`);
                    
                    const correspondingPath = svg.querySelector(`path[data-id="${dataId}"]`);
                    if (correspondingPath) {
                        return correspondingPath;
                    }
                    
                    const pathById = svg.querySelector(`path[id="${dataId}"]`) || 
                                   svg.querySelector(`#${dataId}`);
                    if (pathById) {
                        return pathById;
                    }
                }
            }
        }
        
        return null;
    }

    /**
     * Find which composite contains a state
     * @param {string} stateName - State name
     * @param {Object} metadata - Diagram metadata
     * @returns {string|null} Composite name or null
     */
    findCompositeForState(stateName, metadata) {
        if (!metadata?.diagrams) {
            return null;
        }
        
        for (const [compositeName, compositeData] of Object.entries(metadata.diagrams)) {
            if (compositeName === 'main') continue;
            
            const compositeStates = compositeData.states || [];
            if (compositeStates.includes(stateName)) {
                console.log(`[Composite Lookup] State "${stateName}" found in composite: ${compositeName}`);
                return compositeName;
            }
        }
        
        console.log(`[Composite Lookup] State "${stateName}" not found in any composite`);
        return null;
    }
}
