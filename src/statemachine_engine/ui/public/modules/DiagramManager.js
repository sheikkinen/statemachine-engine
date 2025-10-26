/**
 * DiagramManager - Handles FSM diagram loading, rendering, and navigation
 *
 * VERSION: v1.0.42 (CSS-Only Updates with Metadata-Driven Approach)
 *
 * ARCHITECTURE: Hybrid Fast/Slow Path
 * - FAST PATH: CSS-only updates (~1ms) using metadata-driven lookup table
 * - SLOW PATH: Full Mermaid.run() (~100-150ms) with automatic fallback
 * - First render always uses slow path, subsequent updates use fast path
 * - Addresses v1.0.33-40 failures via metadata-first approach
 * 
 * COMPOSITE STATE LOGIC:
 * - Main diagram: Shows composite states (e.g., "SDXLLIFECYCLE", "QUEUEMANAGEMENT")
 * - Subdiagrams: Show individual states (e.g., "monitoring_sdxl", "checking_queue")
 * - Backend sends: Individual state names (never composite names)
 * - UI mapping: async findCompositeForState() looks up which composite contains state
 * 
 * STATE HIGHLIGHTING FLOW:
 * 1. renderDiagram(highlightState, transition) called
 * 2. If main diagram: findCompositeForState(highlightState) → returns composite name
 * 3. If composite found: Append CSS class to diagram code
 *    - classDef activeComposite fill:#FFD700,stroke:#FF8C00,stroke-width:4px
 *    - class SDXLLIFECYCLE activeComposite
 * 4. If subdiagram: Append CSS class for individual state
 *    - classDef active fill:#90EE90,stroke:#006400,stroke-width:4px
 *    - class monitoring_sdxl active
 * 5. Mermaid.run() processes modified code → renders with highlighting
 * 6. attachCompositeClickHandlers() makes composites clickable
 * 
 * DIAGRAM NAVIGATION:
 * - Main diagram: Overview with composite states (clickable)
 * - Click composite → loadDiagram(machine, compositeName) → show subdiagram
 * - Breadcrumb: "Overview > CompositeName" for navigation
 * 
 * STATE PERSISTENCE:
 * - localStorage stores machine states and transitions
 * - Restored on page reload or diagram switch
 * - Ensures UI shows last known state even after refresh
 * 
 * TRANSITION ARROW HIGHLIGHTING:
 * - highlightTransitionArrowDirect() finds edge by label text
 * - Matches event name in edge labels
 * - Adds .last-transition-arrow class
 * - Auto-clears after 2 seconds
 * 
 * METADATA STRUCTURE:
 * {
 *   "machine_name": "controller",
 *   "diagrams": {
 *     "main": {
 *       "file": "main.mermaid",
 *       "composites": ["SDXLLIFECYCLE", "FACELIFECYCLE", ...]
 *     },
 *     "SDXLLIFECYCLE": {
 *       "file": "SDXLLIFECYCLE.mermaid",
 *       "states": ["monitoring_sdxl", "completing_sdxl_job", ...],
 *       "entry_states": [...],
 *       "exit_states": [...],
 *       "parent": "main"
 *     }
 *   }
 * }
 * 
 * PERFORMANCE:
 * - Full render: ~100-150ms (acceptable for monitoring)
 * - Includes DOM destruction, Mermaid parsing, SVG generation
 * - Visible fade effect (50ms) masks render time
 */
export class DiagramManager {
    constructor(container, breadcrumbNav, logger) {
        this.container = container;
        this.breadcrumbNav = breadcrumbNav;
        this.logger = logger;

        this.currentDiagram = null;
        this.currentDiagramName = 'main';
        this.diagramMetadata = null;
        this.selectedMachine = null;
        this.currentState = null;
        this.currentHighlightedEdge = null;
        this.highlightTimestamp = null;

        // CSS-only update state (v1.0.42+)
        this.stateHighlightMap = null;
    }

    async loadDiagram(machineName, diagramName = 'main') {
        try {
            this.selectedMachine = machineName;
            this.logger.log('info', `Loading diagram for ${machineName}/${diagramName}...`);

            // Clear fast path state when loading new diagram
            this.container.dataset.enriched = 'false';
            this.stateHighlightMap = null;

            // Try new format first
            let response = await fetch(`/api/diagram/${machineName}/${diagramName}`);
            
            if (response.ok) {
                // New format with metadata
                const data = await response.json();
                this.currentDiagram = data.mermaid_code;
                this.currentDiagramName = diagramName;
                this.diagramMetadata = data.metadata;
                
                this.updateBreadcrumb(machineName, diagramName);
                
                // Load persisted state for this machine
                const persistedState = this.loadMachineState(machineName);
                const persistedTransition = this.loadMachineTransition(machineName);
                
                await this.renderDiagram(persistedState, persistedTransition);
                // Click handlers are attached in renderDiagram()
            } else {
                // Fallback to old format
                response = await fetch(`/api/diagram/${machineName}`);
                if (!response.ok) {
                    throw new Error(`Failed to load diagram: ${response.statusText}`);
                }
                
                const data = await response.json();
                this.currentDiagram = data.diagram;
                this.currentDiagramName = 'main';
                this.diagramMetadata = null;
                
                // Load persisted state for this machine
                const persistedState = this.loadMachineState(machineName);
                const persistedTransition = this.loadMachineTransition(machineName);
                
                await this.renderDiagram(persistedState, persistedTransition);
                // Click handlers are attached in renderDiagram()
            }

            this.logger.log('success', `Diagram loaded for ${machineName}`);
        } catch (error) {
            this.logger.log('error', `Failed to load diagram: ${error.message}`);
            this.container.innerHTML = `
                <div class="error">
                    <p>❌ Failed to load diagram</p>
                    <p class="error-detail">${error.message}</p>
                </div>
            `;
        }
    }
    
    /**
     * Load machine state from localStorage
     */
    loadMachineState(machineName) {
        try {
            const persistedStates = localStorage.getItem('machineStates');
            if (persistedStates) {
                const states = JSON.parse(persistedStates);
                const machine = states.find(m => m.machine_name === machineName);
                if (machine && machine.current_state) {
                    console.log(`[DiagramManager] Restored state for ${machineName}: ${machine.current_state}`);
                    return machine.current_state;
                }
            }
        } catch (error) {
            console.error('[DiagramManager] Failed to load persisted state:', error);
        }
        return null;
    }
    
    /**
     * Load machine transition from localStorage
     */
    loadMachineTransition(machineName) {
        try {
            const persistedTransitions = localStorage.getItem('machineTransitions');
            if (persistedTransitions) {
                const transitions = JSON.parse(persistedTransitions);
                const transitionEntry = transitions.find(([name]) => name === machineName);
                if (transitionEntry) {
                    console.log(`[DiagramManager] Restored transition for ${machineName}:`, transitionEntry[1]);
                    return transitionEntry[1];
                }
            }
        } catch (error) {
            console.error('[DiagramManager] Failed to load persisted transition:', error);
        }
        return null;
    }

    async renderDiagram(highlightState = null, transition = null) {
        if (!this.currentDiagram) return;

        // FAST PATH: Attempt CSS-only update if possible (only if already enriched)
        if (highlightState && this.container.dataset.enriched === 'true') {
            const success = this.updateStateHighlight(highlightState, transition?.event);
            if (success) {
                console.log('[Render] ✓ Fast path (~1ms)');
                return;
            }
            console.log('[Render] Fast path failed, using slow path');
        }

        // SLOW PATH: Full Mermaid render (v1.0.30 approach)
        try {
            let diagramCode = this.currentDiagram;
            let compositeToHighlight = null;

            // Context-aware highlighting
            if (highlightState) {
                const currentDiagram = this.diagramMetadata?.diagrams?.[this.currentDiagramName];
                const currentDiagramStates = currentDiagram?.states || [];
                const isMainDiagram = this.currentDiagramName === 'main';

                // If we're on main diagram and have composite states
                if (isMainDiagram) {
                    // Find which composite contains the active state
                    compositeToHighlight = await this.findCompositeForState(highlightState);
                    if (compositeToHighlight) {
                        console.log(`Main diagram: highlighting composite ${compositeToHighlight} containing state ${highlightState}`);
                        diagramCode += `\n\n    classDef activeComposite fill:#FFD700,stroke:#FF8C00,stroke-width:4px`;
                        diagramCode += `\n    class ${compositeToHighlight} activeComposite`;
                    }
                } else if (currentDiagramStates.includes(highlightState)) {
                    // We're in a subdiagram and the state is here - highlight it directly
                    console.log(`Subdiagram: highlighting state ${highlightState}`);
                    diagramCode += `\n\n    classDef active fill:#90EE90,stroke:#006400,stroke-width:4px`;
                    diagramCode += `\n    class ${highlightState} active`;
                }
            }

            // Add redrawing class for fade effect
            this.container.classList.add('redrawing');
            await new Promise(resolve => setTimeout(resolve, 50));

            // Clear container and render new diagram
            this.container.innerHTML = `<pre class="mermaid">${diagramCode}</pre>`;

            // Render with Mermaid
            const mermaidEl = this.container.querySelector('.mermaid');
            await window.mermaid.run({ nodes: [mermaidEl] });

            // Mark container as having diagram
            this.container.classList.add('has-diagram');
            this.container.classList.remove('redrawing');

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

            // Always attach composite click handlers after rendering
            this.attachCompositeClickHandlers();

            // Highlight transition arrow immediately if provided
            if (transition && transition.from && transition.to) {
                console.log(`[DiagramManager] Will highlight arrow for transition:`, transition);
                this.highlightTransitionArrowDirect(transition);
            } else {
                console.log(`[DiagramManager] No valid transition to highlight:`, transition);
            }

            console.log('[Render] ✓ Full render (~150ms)');

        } catch (error) {
            console.error('Error rendering diagram:', error);
            this.logger.log('error', `Diagram rendering failed: ${error.message}`);
            this.container.classList.remove('redrawing');
            this.container.dataset.enriched = 'false';
        }
    }

    updateBreadcrumb(machineName, diagramName) {
        if (!this.breadcrumbNav) return;

        const breadcrumbItems = [];
        
        // Always show "Overview" (main diagram)
        breadcrumbItems.push({
            label: 'Overview',
            diagram: 'main',
            active: diagramName === 'main'
        });
        
        // If showing composite subdiagram, add it
        if (diagramName !== 'main' && this.diagramMetadata) {
            breadcrumbItems.push({
                label: this.diagramMetadata.title || diagramName,
                diagram: diagramName,
                active: true
            });
        }
        
        // Render breadcrumb
        this.breadcrumbNav.innerHTML = breadcrumbItems.map(item => `
            <span class="breadcrumb-item ${item.active ? 'active' : ''}" 
                  data-diagram="${item.diagram}">
                ${item.label}
            </span>
        `).join(' › ');
        
        // Attach click handlers
        this.breadcrumbNav.querySelectorAll('.breadcrumb-item').forEach(item => {
            item.addEventListener('click', () => {
                const targetDiagram = item.dataset.diagram;
                this.loadDiagram(this.selectedMachine, targetDiagram);
            });
        });
    }

    attachCompositeClickHandlers() {
        if (!this.diagramMetadata) {
            console.log('[Composite] No metadata available');
            return;
        }

        const svgEl = this.container.querySelector('svg');
        if (!svgEl) {
            console.log('[Composite] No SVG element found');
            return;
        }
        
        // Get composites from the current diagram in the new metadata structure
        const currentDiagram = this.diagramMetadata.diagrams?.[this.currentDiagramName];
        const composites = currentDiagram?.composites || [];
        console.log('[Composite] Looking for composites:', composites);
        
        composites.forEach(compositeName => {
            // Try multiple selectors to find the composite node
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
                    // Try to find parent node group
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
                    this.loadDiagram(this.selectedMachine, compositeName);
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
                console.log('[Composite] Available IDs:', Array.from(svgEl.querySelectorAll('[id]')).map(el => el.id));
            }
        });
    }

    async findCompositeForState(stateName) {
        if (!this.selectedMachine) return null;

        try {
            const response = await fetch(`/api/diagram/${this.selectedMachine}/metadata`);
            if (!response.ok) return null;
            
            const metadata = await response.json();
            for (const [compositeName, info] of Object.entries(metadata.diagrams)) {
                if (info.states && info.states.includes(stateName)) {
                    return compositeName;
                }
            }
        } catch (error) {
            console.error('Error finding composite for state:', error);
        }
        
        return null;
    }

    updateState(currentState, transition = null) {
        console.log(`[DiagramManager] updateState called with:`);
        console.log(`  currentState: ${currentState}`);
        console.log(`  transition:`, transition);
        
        if (this.currentState === currentState) {
            console.log(`[DiagramManager] State unchanged, but still processing transition`);
        }

        this.currentState = currentState;
        this.renderDiagram(currentState, transition);
    }

    highlightTransitionArrowDirect(transition) {
        const timestamp = Date.now();
        console.log(`[Arrow Highlight Direct] ${timestamp} - Highlighting transition:`, transition);
        
        const svg = this.container.querySelector('svg');
        if (!svg) return;

        // Clear any existing arrow highlights first
        this.clearArrowHighlights(svg);

        const eventTrigger = transition.event;
        const fromState = transition.from;
        const toState = transition.to;
        
        console.log(`[Arrow Highlight Direct] ${timestamp} - Event trigger: "${eventTrigger}" (${fromState} → ${toState})`);
        
        if (eventTrigger && eventTrigger !== 'unknown') {
            console.log(`[Arrow Highlight Direct] ${timestamp} - Searching by event trigger: "${eventTrigger}"`);
            
            // Find edge by matching label text with data-id
            const edge = this.findEdgeByLabel(svg, eventTrigger);
            
            if (edge) {
                console.log(`[Arrow Highlight Direct] ${timestamp} - ✓ Found edge by label matching for "${eventTrigger}"`);
                edge.classList.add('last-transition-arrow');
                
                // Store reference to clear later with timestamp
                this.currentHighlightedEdge = edge;
                this.highlightTimestamp = timestamp;
                
                setTimeout(() => {
                    // Only clear if this is still the current highlight and hasn't been replaced
                    if (edge === this.currentHighlightedEdge && this.highlightTimestamp === timestamp) {
                        console.log(`[Arrow Highlight Direct] ${timestamp} - Clearing highlight after timeout`);
                        edge.classList.remove('last-transition-arrow');
                        this.currentHighlightedEdge = null;
                        this.highlightTimestamp = null;
                    } else {
                        console.log(`[Arrow Highlight Direct] ${timestamp} - Skipping clear - highlight was replaced`);
                    }
                }, 2000);
                return;
            } else {
                console.log(`[Arrow Highlight Direct] ${timestamp} - ✗ Could not find edge by label for "${eventTrigger}"`);
            }
        } else {
            console.log(`[Arrow Highlight Direct] ${timestamp} - No valid event trigger found`);
        }
        
        // No fallback - only highlight if we found the correct edge
        console.log(`[Arrow Highlight Direct] ${timestamp} - ✗ Skipping animation - no specific edge found`);
    }

    highlightTransitionArrow(fromState, toState) {
        console.log(`[Arrow Highlight] Looking for transition: ${fromState} → ${toState}`);
        
        const svg = this.container.querySelector('svg');
        if (!svg) return;

        // Clear any existing arrow highlights first
        this.clearArrowHighlights(svg);

        // Get the event trigger for this transition from stored transitions
        const transition = this.getStoredTransition(fromState, toState);
        const eventTrigger = transition?.event;
        
        console.log(`[Arrow Highlight] Retrieved transition:`, transition);
        console.log(`[Arrow Highlight] Event trigger: "${eventTrigger}"`);
        
        if (eventTrigger && eventTrigger !== 'unknown') {
            console.log(`[Arrow Highlight] Searching by event trigger: "${eventTrigger}"`);
            
            // Find edge by matching label text with data-id
            const edge = this.findEdgeByLabel(svg, eventTrigger);
            
            if (edge) {
                console.log(`[Arrow Highlight] ✓ Found edge by label matching for "${eventTrigger}"`);
                edge.classList.add('last-transition-arrow');
                
                // Store reference to clear later
                this.currentHighlightedEdge = edge;
                
                setTimeout(() => {
                    if (edge === this.currentHighlightedEdge) {
                        edge.classList.remove('last-transition-arrow');
                        this.currentHighlightedEdge = null;
                    }
                }, 2000);
                return;
            } else {
                console.log(`[Arrow Highlight] ✗ Could not find edge by label for "${eventTrigger}"`);
            }
        } else {
            console.log(`[Arrow Highlight] No valid event trigger found`);
        }
        
        // No fallback - only highlight if we found the correct edge
        console.log(`[Arrow Highlight] ✗ Skipping animation - no specific edge found`);
    }

    clearArrowHighlights(svg) {
        // Remove highlight class from all edges
        const highlightedEdges = svg.querySelectorAll('.last-transition-arrow');
        if (highlightedEdges.length > 0) {
            console.log(`[Clear Highlights] Clearing ${highlightedEdges.length} existing highlights`);
            highlightedEdges.forEach(edge => {
                edge.classList.remove('last-transition-arrow');
            });
        }
        
        // Clear current reference
        this.currentHighlightedEdge = null;
        this.highlightTimestamp = null;
    }

    findEdgeByLabel(svg, eventTrigger) {
        // Look for edge labels containing the event trigger text
        const edgeLabels = svg.querySelectorAll('g.edgeLabels g.label');
        
        for (const label of edgeLabels) {
            // Check if this label contains the event trigger text
            const labelText = label.textContent || '';
            if (labelText.includes(eventTrigger)) {
                // Get the data-id from this label
                const dataId = label.getAttribute('data-id');
                if (dataId) {
                    console.log(`[Arrow Highlight] Found label with event "${eventTrigger}", data-id: "${dataId}"`);
                    
                    // Find the corresponding path with matching data-id
                    const correspondingPath = svg.querySelector(`path[data-id="${dataId}"]`);
                    if (correspondingPath) {
                        return correspondingPath;
                    }
                    
                    // Alternative: try finding by ID if data-id doesn't work
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

    getStoredTransition(fromState, toState) {
        // Look up transition info from the machine state manager's stored transitions
        if (!this.selectedMachine) return null;
        
        // Try to access the stored transition from localStorage or from the machine manager
        try {
            const persistedTransitions = localStorage.getItem('machineTransitions');
            if (persistedTransitions) {
                const transitions = JSON.parse(persistedTransitions);
                const transitionEntry = transitions.find(([name]) => name === this.selectedMachine);
                if (transitionEntry && transitionEntry[1]) {
                    const transition = transitionEntry[1];
                    if (transition.from === fromState && transition.to === toState) {
                        return transition;
                    }
                }
            }
        } catch (error) {
            console.error('[Arrow Highlight] Failed to get stored transition:', error);
        }
        
        return null;

        if (edge) {
            console.log(`[Arrow Highlight] ✓ Found transition arrow`);
            edge.classList.add('last-transition-arrow');
            setTimeout(() => {
                edge.classList.remove('last-transition-arrow');
            }, 2000);
        } else {
            console.log(`[Arrow Highlight] ✗ No edges found, debugging available elements...`);
            this.debugSvgElements(svg);
        }
    }

    debugSvgElements(svg) {
        console.log(`[SVG Debug] Available elements:`);
        
        // Check edge labels specifically
        const edgeLabels = svg.querySelectorAll('g.edgeLabels g.label');
        console.log(`[SVG Debug] Found ${edgeLabels.length} edge label elements:`);
        edgeLabels.forEach((label, index) => {
            const dataId = label.getAttribute('data-id');
            const text = label.textContent?.trim() || 'No text';
            console.log(`  Label ${index}: data-id="${dataId}", text="${text}"`);
        });
        
        // Check all paths
        const paths = svg.querySelectorAll('path');
        console.log(`[SVG Debug] Found ${paths.length} path elements:`);
        paths.forEach((path, index) => {
            const dataId = path.getAttribute('data-id');
            const id = path.id;
            const className = path.className.baseVal || path.getAttribute('class');
            console.log(`  Path ${index}: id="${id}", data-id="${dataId}", class="${className}"`);
        });
        
        // Check for common Mermaid edge classes
        const commonSelectors = [
            'path.edge',
            'path[class*="edge"]', 
            '.flowchart-link',
            'path[class*="link"]',
            'path[class*="transition"]',
            '[data-id*="new_job"]',
            '[data-id*="initialized"]',
            '[data-id*="no_jobs"]'
        ];
        
        commonSelectors.forEach(selector => {
            const elements = svg.querySelectorAll(selector);
            if (elements.length > 0) {
                console.log(`[SVG Debug] Found ${elements.length} elements with selector "${selector}"`);
                elements.forEach((el, i) => {
                    const dataId = el.getAttribute('data-id');
                    const id = el.id;
                    const className = el.className.baseVal || el.getAttribute('class');
                    console.log(`    Element ${i}: id="${id}", data-id="${dataId}", class="${className}"`);
                });
            }
        });
    }

    /**
     * Build state highlight lookup map from metadata
     * Pre-computes what to highlight for each state (composite vs individual)
     * Called ONCE after each diagram render
     *
     * @returns {Object|null} Map of state → {type, target, class} or null if no metadata
     */
    buildStateHighlightMap() {
        const map = {};

        if (!this.diagramMetadata?.diagrams) {
            console.warn('[Map] No metadata - will fallback to full render');
            return null;
        }

        const currentDiagram = this.diagramMetadata.diagrams[this.currentDiagramName];
        if (!currentDiagram) {
            console.warn(`[Map] No metadata for ${this.currentDiagramName}`);
            return null;
        }

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

    /**
     * Enrich SVG with data attributes for fast DOM queries
     * Adds data-state-id to state nodes and data-edge-event to transition arrows
     * Uses stateHighlightMap to know which nodes to enrich
     *
     * @returns {boolean} True if enrichment succeeded, false otherwise
     */
    enrichSvgWithDataAttributes() {
        const svg = this.container.querySelector('svg');
        if (!svg || !this.stateHighlightMap) return false;

        let enrichedCount = 0;
        const targets = new Set(Object.values(this.stateHighlightMap).map(e => e.target));
        const enrichedNodes = [];

        // Enrich state nodes (supports both flowchart and statediagram)
        const stateNodes = svg.querySelectorAll('g.node, g.statediagram-state');
        stateNodes.forEach(node => {
            // Flowchart: text in <text> element
            // Statediagram: text in <p> element inside <foreignObject>
            const textEl = node.querySelector('text');
            const pEl = node.querySelector('p');
            const stateName = (pEl?.textContent?.trim() || textEl?.textContent?.trim() || '');

            if (stateName && targets.has(stateName)) {
                node.dataset.stateId = stateName;
                enrichedCount++;
                enrichedNodes.push({
                    stateName,
                    classes: node.className.baseVal || node.getAttribute('class'),
                    id: node.id
                });
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
        if (enrichedNodes.length > 0) {
            console.log('[Enrich] Enriched nodes:', enrichedNodes);
        }
        return enrichedCount > 0;
    }

    /**
     * Update state highlight using CSS-only approach (FAST PATH)
     * Lookup state in map → Query by data attribute → Toggle CSS class
     * Returns false to trigger fallback to full render if anything fails
     *
     * @param {string} stateName - State to highlight
     * @param {string} eventName - Optional event for transition arrow
     * @returns {boolean} True if CSS-only update succeeded, false to trigger fallback
     */
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
                console.log(`[CSS-only] ✓ Arrow: ${eventName}`);

                setTimeout(() => {
                    edge.classList.remove('last-transition-arrow');
                }, 2000);
            }
        }

        return true;
    }
}
