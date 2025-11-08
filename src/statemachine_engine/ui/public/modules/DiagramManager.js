/**
 * DiagramManager - Coordinates diagram loading and state updates
 * 
 * VERSION: v1.0.54 (Modular Architecture)
 * 
 * REFACTORED: Extracted rendering and highlighting to separate modules
 * - MermaidRenderer: Handles Mermaid rendering and SVG enrichment
 * - EventHighlighter: Handles state highlighting and transition animations
 * - DiagramManager: Slim coordinator that delegates to above modules
 * 
 * Responsibilities:
 * - Load diagram metadata and Mermaid code
 * - Coordinate rendering via MermaidRenderer
 * - Coordinate highlighting via EventHighlighter
 * - Handle breadcrumb navigation
 * - Manage composite state navigation
 * - Persist/restore machine state
 * - Lazy loading of config metadata (Phase 3 UI refresh)
 */

import { StateGroupManager } from './StateGroupManager.js';
import { MermaidRenderer } from './MermaidRenderer.js';
import { EventHighlighter } from './EventHighlighter.js';

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

        // Modular components
        this.renderer = new MermaidRenderer(container, logger);
        this.highlighter = new EventHighlighter(container, logger);
        this.stateGroupManager = new StateGroupManager(null);
    }

    async loadDiagram(machineName, diagramName = 'main') {
        try {
            this.selectedMachine = machineName;
            this.logger.log('info', `Loading diagram for ${machineName}/${diagramName}...`);

            // Clear fast path state when loading new diagram
            this.renderer.clearFastPath();

            // Try new format first
            let response = await fetch(`/api/diagram/${machineName}/${diagramName}`);
            
            if (response.ok) {
                // New format with metadata
                const data = await response.json();
                this.currentDiagram = data.mermaid_code;
                this.currentDiagramName = diagramName;
                this.diagramMetadata = data.metadata;
                
                // Update state group manager with new metadata
                this.stateGroupManager.setMetadata(data.metadata);
                
                this.updateBreadcrumb(machineName, diagramName);
                
                // Load persisted state for this machine
                const persistedState = this.loadMachineState(machineName);
                const persistedTransition = this.loadMachineTransition(machineName);
                
                await this.renderDiagram(persistedState, persistedTransition);
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
                
                const persistedState = this.loadMachineState(machineName);
                const persistedTransition = this.loadMachineTransition(machineName);
                
                await this.renderDiagram(persistedState, persistedTransition);
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

        // FAST PATH: Attempt CSS-only update if possible
        if (highlightState && this.container.dataset.enriched === 'true') {
            const stateHighlightMap = this.renderer.getStateHighlightMap();
            const success = this.highlighter.updateStateHighlight(
                highlightState,
                stateHighlightMap,
                this.diagramMetadata,
                this.currentDiagramName,
                transition?.event
            );
            
            if (success) {
                console.log('[Render] ✓ Fast path (~1ms)');
                return;
            }
            console.log('[Render] Fast path failed, using slow path');
        }

        // SLOW PATH: Full Mermaid render
        try {
            // Prepare metadata with current diagram name
            const metadata = {
                ...this.diagramMetadata,
                currentDiagramName: this.currentDiagramName
            };

            // Render via MermaidRenderer
            await this.renderer.render(this.currentDiagram, metadata);

            // Attach composite click handlers
            this.renderer.attachCompositeClickHandlers(
                this.diagramMetadata,
                this.currentDiagramName,
                (compositeName) => this.loadDiagram(this.selectedMachine, compositeName)
            );

            // Apply highlighting if needed
            if (highlightState) {
                const stateHighlightMap = this.renderer.getStateHighlightMap();
                this.highlighter.updateStateHighlight(
                    highlightState,
                    stateHighlightMap,
                    this.diagramMetadata,
                    this.currentDiagramName,
                    transition?.event
                );
            }

            // Highlight transition arrow if provided
            if (transition) {
                this.highlighter.highlightTransitionArrow(transition);
            }

        } catch (error) {
            console.error('Error rendering diagram:', error);
            this.logger.log('error', `Diagram rendering failed: ${error.message}`);
        }
    }

    updateBreadcrumb(machineName, diagramName) {
        if (!this.breadcrumbNav) return;

        const breadcrumbItems = [];
        
        breadcrumbItems.push({
            label: 'Overview',
            diagram: 'main',
            active: diagramName === 'main'
        });
        
        if (diagramName !== 'main' && this.diagramMetadata) {
            breadcrumbItems.push({
                label: this.diagramMetadata.title || diagramName,
                diagram: diagramName,
                active: true
            });
        }
        
        this.breadcrumbNav.innerHTML = breadcrumbItems.map(item => `
            <span class="breadcrumb-item ${item.active ? 'active' : ''}" 
                  data-diagram="${item.diagram}">
                ${item.label}
            </span>
        `).join(' › ');
        
        this.breadcrumbNav.querySelectorAll('.breadcrumb-item').forEach(item => {
            item.addEventListener('click', () => {
                const targetDiagram = item.dataset.diagram;
                this.loadDiagram(this.selectedMachine, targetDiagram);
            });
        });
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
    
    getStates() {
        return this.stateGroupManager.getStates(this.currentDiagramName);
    }
    
    getStateGroups() {
        return this.stateGroupManager.getStateGroups(this.currentDiagramName);
    }

    hasConfig(configType) {
        try {
            const cachedMetadata = localStorage.getItem(`diagram_metadata_${configType}`);
            return !!cachedMetadata;
        } catch (error) {
            console.error(`[DiagramManager] Error checking config cache:`, error);
            return false;
        }
    }

    async fetchConfigMetadata(configType) {
        try {
            console.log(`[DiagramManager] Fetching metadata for: ${configType}`);
            const response = await fetch(`/api/diagram/${configType}/metadata`);
            
            if (!response.ok) {
                console.warn(`[DiagramManager] Failed to fetch metadata for ${configType}: ${response.status}`);
                return null;
            }
            
            const metadata = await response.json();
            
            try {
                localStorage.setItem(`diagram_metadata_${configType}`, JSON.stringify(metadata));
            } catch (error) {
                console.warn(`[DiagramManager] Failed to cache metadata for ${configType}:`, error);
            }
            
            console.log(`[DiagramManager] ✓ Fetched and cached metadata for ${configType}`);
            return metadata;
            
        } catch (error) {
            console.error(`[DiagramManager] Error fetching metadata for ${configType}:`, error);
            return null;
        }
    }
}
