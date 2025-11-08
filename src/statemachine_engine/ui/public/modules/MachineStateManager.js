/**
 * MachineStateManager - Handles machine state tracking and UI updates
 */
export class MachineStateManager {
    constructor(container, statusElements, logger) {
        this.machines = new Map();
        this.lastTransitions = new Map();
        this.container = container;
        this.statusElements = statusElements;
        this.logger = logger;
        
        // Load persisted state from localStorage
        this.loadPersistedState();
    }
    
    /**
     * Load machine states from localStorage
     */
    loadPersistedState() {
        try {
            const persistedStates = localStorage.getItem('machineStates');
            if (persistedStates) {
                const states = JSON.parse(persistedStates);
                states.forEach(machine => {
                    this.machines.set(machine.machine_name, machine);
                });
                console.log('[StateManager] Loaded persisted states for', this.machines.size, 'machines');
            }
            
            const persistedTransitions = localStorage.getItem('machineTransitions');
            if (persistedTransitions) {
                const transitions = JSON.parse(persistedTransitions);
                transitions.forEach(([machineName, transition]) => {
                    this.lastTransitions.set(machineName, transition);
                });
                console.log('[StateManager] Loaded persisted transitions for', this.lastTransitions.size, 'machines');
            }
        } catch (error) {
            console.error('[StateManager] Failed to load persisted state:', error);
        }
    }
    
    /**
     * Save machine states to localStorage
     */
    persistState() {
        try {
            const states = Array.from(this.machines.values());
            localStorage.setItem('machineStates', JSON.stringify(states));
            
            const transitions = Array.from(this.lastTransitions.entries());
            localStorage.setItem('machineTransitions', JSON.stringify(transitions));
            
            console.debug('[StateManager] Persisted state for', states.length, 'machines');
        } catch (error) {
            console.error('[StateManager] Failed to persist state:', error);
        }
    }

    updateMachines(machines) {
        // Clear localStorage on fresh machine list update
        if (machines && machines.length > 0) {
            localStorage.removeItem('machineStates');
            localStorage.removeItem('machineTransitions');
        }
        
        this.machines.clear();
        machines.forEach(machine => {
            this.machines.set(machine.machine_name, machine);
        });

        // Update status bar
        if (this.statusElements.total) {
            this.statusElements.total.textContent = machines.length;
        }
        if (this.statusElements.active) {
            this.statusElements.active.textContent = machines.length;
        }
        if (this.statusElements.lastUpdate) {
            this.statusElements.lastUpdate.textContent = new Date().toLocaleTimeString();
        }

        this.renderMachines();
        this.persistState();
    }

    handleStateChange(data) {
        const machineName = data.machine_name;
        const payload = data.payload || {};
        
        // Debug: log the full payload structure
        console.log(`[StateChange Debug] Full payload:`, payload);
        console.log(`[StateChange Debug] Available keys:`, Object.keys(payload));
        
        // Store last transition
        if (payload.from_state && payload.to_state) {
            this.lastTransitions.set(machineName, {
                from: payload.from_state,
                to: payload.to_state,
                event: payload.event_trigger || payload.event || payload.event_name || payload.trigger || 'unknown',
                timestamp: payload.timestamp || Date.now() / 1000
            });
            console.log(`[Transition] ${machineName}: ${payload.from_state} → ${payload.to_state}`);
            console.log(`[Transition Debug] Event trigger: "${payload.event_trigger}"`);
        }
        
        // Update machine state in map
        let machine = this.machines.get(machineName);
        if (!machine) {
            machine = {
                machine_name: machineName,
                current_state: payload.to_state,
                last_activity: payload.timestamp || Date.now() / 1000,
                metadata: null
            };
            this.machines.set(machineName, machine);
            this.renderMachines();
            this.logger.log('info', `New machine detected: ${machineName}`);
        } else {
            console.log(`[MachineStateManager] Updating existing machine: ${machineName}`);
            machine.current_state = payload.to_state;
            machine.last_activity = payload.timestamp || Date.now() / 1000;
            this.machines.set(machineName, machine);
            console.log(`[MachineStateManager] Calling updateMachineCard for ${machineName}`);
            this.updateMachineCard(machine);
        }
        
        // Log transition
        if (payload.from_state && payload.to_state) {
            this.logger.log('info', `${machineName}: ${payload.from_state} → ${payload.to_state}`);
        }

        // Persist updated state to localStorage
        this.persistState();

        const returnedTransition = this.lastTransitions.get(machineName);
        console.log(`[StateManager] Returning transition:`, returnedTransition);

        return { machine, transition: returnedTransition };
    }

    getMachine(machineName) {
        return this.machines.get(machineName);
    }

    getTransition(machineName) {
        return this.lastTransitions.get(machineName);
    }

    updateMachineCard(machine) {
        console.log(`[MachineStateManager] updateMachineCard called for ${machine.machine_name}, state: ${machine.current_state}`);
        
        // Find all card instances (kanban cards and machine panel cards)
        const cardElements = document.querySelectorAll(`[data-machine="${machine.machine_name}"]`);
        
        cardElements.forEach(cardEl => {
            // Check if it's a kanban card (simpler structure)
            if (cardEl.classList.contains('kanban-card')) {
                console.log(`[MachineStateManager] Updating kanban card for ${machine.machine_name}`);
                // Kanban cards just show the machine name, no state update needed here
                // State is managed by KanbanView.updateCard which moves cards between columns
            } 
            // Check if it's a machine panel card (detailed structure)
            else if (cardEl.classList.contains('machine-card')) {
                console.log(`[MachineStateManager] Updating machine panel card for ${machine.machine_name}`);
                const stateEl = cardEl.querySelector('.info-value');
                if (stateEl) {
                    console.log(`[MachineStateManager] Updating state text to: ${machine.current_state}`);
                    stateEl.textContent = machine.current_state || 'Unknown';
                } else {
                    console.warn(`[MachineStateManager] State element not found in machine card for ${machine.machine_name}`);
                }
                const activityEl = cardEl.querySelectorAll('.info-value')[1];
                if (activityEl) {
                    const lastActivity = machine.last_activity ?
                        new Date(machine.last_activity * 1000).toLocaleString() : 'Never';
                    activityEl.textContent = lastActivity;
                }
            }
        });
    }

    renderMachines() {
        this.container.innerHTML = '';
        
        this.machines.forEach(machine => {
            const cardEl = this.createMachineCard(machine);
            this.container.appendChild(cardEl);
        });
    }

    createMachineCard(machine) {
        const card = document.createElement('div');
        card.className = 'machine-card';
        card.setAttribute('data-machine', machine.machine_name);

        const lastActivity = machine.last_activity ? 
            new Date(machine.last_activity * 1000).toLocaleString() : 'Never';

        card.innerHTML = `
            <div class="machine-header">
                <div class="machine-name">${machine.machine_name}</div>
            </div>
            
            <div class="machine-info">
                <div class="info-row">
                    <span class="info-label">Current State:</span>
                    <span class="info-value">${machine.current_state || 'Unknown'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Last Activity:</span>
                    <span class="info-value">${lastActivity}</span>
                </div>
            </div>
        `;

        return card;
    }
}
