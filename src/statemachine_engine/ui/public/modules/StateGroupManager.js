/**
 * StateGroupManager Module
 * 
 * Handles extraction of states and state groups from diagram metadata.
 * Used by KanbanView to organize columns into groups.
 */

export class StateGroupManager {
    constructor(diagramMetadata) {
        this.metadata = diagramMetadata;
    }
    
    /**
     * Update metadata (called when diagram changes)
     */
    setMetadata(metadata) {
        this.metadata = metadata;
    }
    
    /**
     * Get the list of states for a specific diagram
     * 
     * @param {string} diagramName - Name of the diagram (e.g., 'main', 'IDLE', 'PROCESSING')
     * @returns {string[]|null} Array of state names or null if not available
     */
    getStates(diagramName = 'main') {
        if (!this.metadata?.diagrams) {
            return null;
        }
        
        const diagram = this.metadata.diagrams[diagramName];
        if (!diagram) {
            return null;
        }
        
        // For subdiagrams, return the states directly
        if (diagramName !== 'main' && diagram.states) {
            return diagram.states;
        }
        
        // For main diagram, collect all states from all composites
        if (diagramName === 'main') {
            const allStates = new Set();
            for (const [compositeName, compositeData] of Object.entries(this.metadata.diagrams)) {
                if (compositeName === 'main') continue;
                if (compositeData.states && Array.isArray(compositeData.states)) {
                    compositeData.states.forEach(state => allStates.add(state));
                }
            }
            return Array.from(allStates).sort();
        }
        
        return null;
    }
    
    /**
     * Get state groups for a specific diagram
     * Groups are only returned for the main diagram (composite view)
     * 
     * @param {string} diagramName - Name of the diagram
     * @returns {Array<{name: string, states: string[]}>|null} Array of state groups or null
     */
    getStateGroups(diagramName = 'main') {
        if (!this.metadata?.diagrams) {
            return null;
        }
        
        const diagram = this.metadata.diagrams[diagramName];
        if (!diagram) {
            return null;
        }
        
        // Only provide groups for main diagram (composite view)
        if (diagramName === 'main' && diagram.composites) {
            const groups = [];
            
            // Iterate through composites in the order they appear in metadata
            // This preserves the order from the YAML file
            for (const compositeName of diagram.composites) {
                const compositeData = this.metadata.diagrams[compositeName];
                if (compositeData && compositeData.states) {
                    groups.push({
                        name: compositeName,
                        states: compositeData.states
                    });
                }
            }
            
            return groups.length > 0 ? groups : null;
        }
        
        // For subdiagrams, no groups (flat display)
        return null;
    }
    
    /**
     * Find which composite group a state belongs to
     * 
     * @param {string} stateName - Name of the state to look up
     * @returns {string|null} Name of the composite group or null if not found
     */
    findGroupForState(stateName) {
        if (!this.metadata?.diagrams) {
            return null;
        }
        
        for (const [compositeName, compositeData] of Object.entries(this.metadata.diagrams)) {
            if (compositeName === 'main') continue;
            
            if (compositeData.states && compositeData.states.includes(stateName)) {
                return compositeName;
            }
        }
        
        return null;
    }
    
    /**
     * Get all composites (state groups) from the main diagram
     * 
     * @returns {string[]|null} Array of composite names or null
     */
    getComposites() {
        if (!this.metadata?.diagrams?.main?.composites) {
            return null;
        }
        
        return this.metadata.diagrams.main.composites;
    }
}
