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
        this.machines.clear();
        machines.forEach(machine => {
            this.machines.set(machine.machine_name, machine);
        });

        // Update status bar
        const activeMachines = machines.filter(m => m.running).length;
        if (this.statusElements.total) {
            this.statusElements.total.textContent = machines.length;
        }
        if (this.statusElements.active) {
            this.statusElements.active.textContent = activeMachines;
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
        
        // Store last transition
        if (payload.from_state && payload.to_state) {
            this.lastTransitions.set(machineName, {
                from: payload.from_state,
                to: payload.to_state,
                event: payload.event || 'unknown',
                timestamp: payload.timestamp || Date.now() / 1000
            });
            console.log(`[Transition] ${machineName}: ${payload.from_state} → ${payload.to_state}`);
        }
        
        // Update machine state in map
        let machine = this.machines.get(machineName);
        if (!machine) {
            machine = {
                machine_name: machineName,
                current_state: payload.to_state,
                last_activity: payload.timestamp || Date.now() / 1000,
                running: true,
                metadata: null
            };
            this.machines.set(machineName, machine);
            this.renderMachines();
            this.logger.log('info', `New machine detected: ${machineName}`);
        } else {
            machine.current_state = payload.to_state;
            machine.last_activity = payload.timestamp || Date.now() / 1000;
            machine.running = true;
            this.machines.set(machineName, machine);
            this.updateMachineCard(machine);
        }
        
        // Log transition
        if (payload.from_state && payload.to_state) {
            this.logger.log('info', `${machineName}: ${payload.from_state} → ${payload.to_state}`);
        }

        // Persist updated state to localStorage
        this.persistState();

        return { machine, transition: this.lastTransitions.get(machineName) };
    }

    getMachine(machineName) {
        return this.machines.get(machineName);
    }

    getTransition(machineName) {
        return this.lastTransitions.get(machineName);
    }

    updateMachineCard(machine) {
        const cardEl = document.querySelector(`[data-machine="${machine.machine_name}"]`);
        if (cardEl) {
            const stateEl = cardEl.querySelector('.info-value');
            if (stateEl) {
                stateEl.textContent = machine.current_state || 'Unknown';
            }
            const activityEl = cardEl.querySelectorAll('.info-value')[1];
            if (activityEl) {
                const lastActivity = machine.last_activity ? 
                    new Date(machine.last_activity).toLocaleString() : 'Never';
                activityEl.textContent = lastActivity;
            }
        }
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

        const statusClass = machine.running ? 'running' : 'stopped';
        const statusText = machine.running ? 'Running' : 'Stopped';
        
        const lastActivity = machine.last_activity ? 
            new Date(machine.last_activity).toLocaleString() : 'Never';

        card.innerHTML = `
            <div class="machine-header">
                <div class="machine-name">${machine.machine_name}</div>
                <div class="status-indicator">
                    <div class="status-dot ${statusClass}"></div>
                    <span class="status-text ${statusClass}">${statusText}</span>
                </div>
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
            
            <div class="machine-controls">
                <button class="btn btn-start" 
                        data-action="start"
                        data-machine="${machine.machine_name}"
                        ${machine.running ? 'disabled' : ''}>
                    Start
                </button>
                <button class="btn btn-stop" 
                        data-action="stop"
                        data-machine="${machine.machine_name}"
                        ${!machine.running ? 'disabled' : ''}>
                    Stop
                </button>
            </div>
        `;

        // Attach event listeners
        card.querySelector('.btn-start').addEventListener('click', (e) => {
            this.startMachine(e.target.dataset.machine);
        });
        card.querySelector('.btn-stop').addEventListener('click', (e) => {
            this.stopMachine(e.target.dataset.machine);
        });

        return card;
    }

    async startMachine(machineName) {
        try {
            this.logger.log('info', `Starting machine: ${machineName}`);
            
            const response = await fetch(`/api/machine/${machineName}/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.logger.log('success', `${result.message} (PID: ${result.pid})`);
            } else {
                this.logger.log('error', `Failed to start ${machineName}: ${result.error}`);
            }
        } catch (error) {
            this.logger.log('error', `Error starting ${machineName}: ${error.message}`);
        }
    }

    async stopMachine(machineName) {
        try {
            this.logger.log('info', `Stopping machine: ${machineName}`);
            
            const response = await fetch(`/api/machine/${machineName}/stop`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.logger.log('success', result.message);
            } else {
                this.logger.log('error', `Failed to stop ${machineName}: ${result.error}`);
            }
        } catch (error) {
            this.logger.log('error', `Error stopping ${machineName}: ${error.message}`);
        }
    }
}
