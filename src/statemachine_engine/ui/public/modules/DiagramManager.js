/**
 * DiagramManager - Handles FSM diagram loading, rendering, and navigation
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
    }

    async loadDiagram(machineName, diagramName = 'main') {
        try {
            this.selectedMachine = machineName;
            this.logger.log('info', `Loading diagram for ${machineName}/${diagramName}...`);

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

        try {
            let diagramCode = this.currentDiagram;
            let compositeToHighlight = null;

            // Context-aware highlighting
            if (highlightState) {
                const currentDiagramStates = this.diagramMetadata?.states || [];
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

            // Always attach composite click handlers after rendering
            this.attachCompositeClickHandlers();

            // Highlight transition arrow immediately if provided
            if (transition && transition.from && transition.to) {
                console.log(`[DiagramManager] Will highlight arrow for transition:`, transition);
                this.highlightTransitionArrowDirect(transition);
            } else {
                console.log(`[DiagramManager] No valid transition to highlight:`, transition);
            }
        } catch (error) {
            console.error('Error rendering diagram:', error);
            this.logger.log('error', `Diagram rendering failed: ${error.message}`);
            this.container.classList.remove('redrawing');
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
        
        const composites = this.diagramMetadata.composites || [];
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
}
