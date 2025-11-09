/**
 * KanbanView Module
 * 
 * Displays FSM instances as cards in columns based on their current state.
 * Supports both flat state list and grouped state organization.
 */

export default class KanbanView {
    constructor(container, templateName, states, logger, stateGroups = null) {
        this.container = container;
        this.templateName = templateName;
        this.states = states;
        this.logger = logger;
        this.stateGroups = stateGroups; // [{name: 'GROUP_NAME', states: ['state1', 'state2']}]
        this.cards = {};
        this.isVisible = false;
        this.columns = {};
    }

    /**
     * Render the Kanban board with columns for each state
     * If state groups are provided, organize columns by groups
     */
    render() {
        // Add kanban-view class to container
        this.container.classList.add('kanban-view');
        
        // Clear existing content
        this.container.innerHTML = '';
        
        if (this.stateGroups && this.stateGroups.length > 0) {
            // Render with groups
            this._renderGrouped();
        } else {
            // Render flat (original behavior)
            this._renderFlat();
        }
        
        // Don't hide here - visibility is managed by app-modular.js
    }
    
    /**
     * Render grouped columns (new feature)
     * Groups flow left-to-right, states top-to-bottom within each group
     */
    _renderGrouped() {
        this.stateGroups.forEach(group => {
            const groupContainer = document.createElement('div');
            groupContainer.className = 'kanban-group';
            groupContainer.setAttribute('data-group', group.name);
            
            // Group header
            const groupHeader = document.createElement('div');
            groupHeader.className = 'kanban-group-header';
            groupHeader.textContent = group.name;
            groupContainer.appendChild(groupHeader);
            
            // States container for this group (vertical stack)
            const statesContainer = document.createElement('div');
            statesContainer.className = 'kanban-group-states';
            
            // Create state section for each state in the group
            group.states.forEach(state => {
                const stateSection = document.createElement('div');
                stateSection.className = 'kanban-group-state';
                stateSection.setAttribute('data-state', state);
                
                // State heading
                const stateHeading = document.createElement('div');
                stateHeading.className = 'kanban-state-heading';
                stateHeading.textContent = state;
                stateSection.appendChild(stateHeading);
                
                // Cards container for this state
                const cardsContainer = document.createElement('div');
                cardsContainer.className = 'kanban-state-cards';
                stateSection.appendChild(cardsContainer);
                
                // Store reference to this state's container
                this.columns[state] = stateSection;
                
                statesContainer.appendChild(stateSection);
            });
            
            groupContainer.appendChild(statesContainer);
            this.container.appendChild(groupContainer);
        });
    }
    
    /**
     * Render flat columns (original behavior)
     */
    _renderFlat() {
        this.states.forEach(state => {
            const column = this._createColumn(state);
            this.columns[state] = column;
            this.container.appendChild(column);
        });
    }

    /**
     * Create a column element for a state
     */
    _createColumn(state) {
        const column = document.createElement('div');
        column.className = 'kanban-column';
        column.setAttribute('data-state', state);
        
        // Column header
        const header = document.createElement('div');
        header.className = 'kanban-column-header';
        header.textContent = state;
        column.appendChild(header);
        
        // Cards container
        const cardsContainer = document.createElement('div');
        cardsContainer.className = 'kanban-cards';
        column.appendChild(cardsContainer);
        
        return column;
    }

    /**
     * Add a machine card to a state column
     */
    addCard(machineName, state) {
        // Validate state exists
        if (!this.states.includes(state)) {
            console.warn(`[KanbanView] State '${state}' not in configured states list for ${machineName}`);
            console.warn(`[KanbanView] Available states:`, this.states);
            return;
        }
        
        // Validate column exists
        const column = this.columns[state];
        if (!column) {
            console.error(`[KanbanView] Column not found for state '${state}' for machine ${machineName}`);
            console.error(`[KanbanView] Available columns:`, Object.keys(this.columns));
            console.error(`[KanbanView] Template:`, this.templateName);
            return;
        }
        
        // Create card element
        const card = document.createElement('div');
        card.className = 'kanban-card';
        card.setAttribute('data-machine', machineName);
        card.textContent = machineName;
        
        // Add to column
        const cardsContainer = column.querySelector('.kanban-cards, .kanban-state-cards');
        if (!cardsContainer) {
            console.error(`[KanbanView] Cards container not found in column for state '${state}'`);
            return;
        }
        cardsContainer.appendChild(card);
        
        // Track card
        this.cards[machineName] = {
            element: card,
            state: state
        };
    }

    /**
     * Update a card's state (move to new column)
     */
    updateCard(machineName, newState) {
        // Check if card exists
        if (!this.cards[machineName]) {
            console.warn(`[KanbanView] Card not found: ${machineName}`);
            if (this.logger && this.logger.log) {
                this.logger.log('warning', `Kanban card not found: ${machineName}`);
            }
            return;
        }
        
        const cardInfo = this.cards[machineName];
        
        // Skip if already in target state
        if (cardInfo.state === newState) {
            return;
        }
        
        // Validate new state
        if (!this.states.includes(newState)) {
            console.error(`[KanbanView] Invalid state: ${newState} for ${machineName}`);
            console.error(`[KanbanView] Available states:`, this.states);
            if (this.logger && this.logger.log) {
                this.logger.log('error', `Invalid kanban state: ${newState} for ${machineName}`);
            }
            return;
        }
        
        // Validate new column exists
        const newColumn = this.columns[newState];
        if (!newColumn) {
            console.error(`[KanbanView] Column not found for state '${newState}' when updating ${machineName}`);
            console.error(`[KanbanView] Available columns:`, Object.keys(this.columns));
            return;
        }
        
        // Remove from old column
        cardInfo.element.remove();
        
        // Add to new column
        const cardsContainer = newColumn.querySelector('.kanban-cards, .kanban-state-cards');
        if (!cardsContainer) {
            console.error(`[KanbanView] Cards container not found in column for state '${newState}'`);
            return;
        }
        cardsContainer.appendChild(cardInfo.element);
        
        // Update tracking
        cardInfo.state = newState;
    }

    /**
     * Remove a card (machine terminated)
     */
    removeCard(machineName) {
        if (!this.cards[machineName]) {
            this.logger.warn(`Card not found: ${machineName}`);
            return;
        }
        
        // Remove element
        this.cards[machineName].element.remove();
        
        // Remove from tracking
        delete this.cards[machineName];
    }

    /**
     * Show the Kanban view
     */
    show() {
        this.container.style.display = '';
        this.container.classList.add('kanban-visible');
        this.isVisible = true;
    }

    /**
     * Hide the Kanban view
     */
    hide() {
        this.container.style.display = 'none';
        this.container.classList.remove('kanban-visible');
        this.isVisible = false;
    }
}
