/**
 * Main Application - State Machine Monitor
 * Orchestrates all modules for real-time state machine monitoring
 */

import { WebSocketManager } from './modules/WebSocketManager.js';
import { DiagramManager } from './modules/DiagramManager.js';
import { MachineStateManager } from './modules/MachineStateManager.js';
import { ActivityLogger } from './modules/ActivityLogger.js';

class StateMachineMonitor {
    constructor() {
        this.initializeUI();
        this.initializeModules();
        this.initializeDiagramTabs();
        
        // Start connections
        this.wsManager.connect();
        
        // Load diagram for first available machine after machines are loaded
        this.loadInitialDiagram();
    }
    
    async loadInitialDiagram() {
        try {
            // Wait a bit for machines to be fetched
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Get machines from the machine manager (it's a Map)
            const machines = Array.from(this.machineManager.machines.values());
            
            if (machines && machines.length > 0) {
                const firstMachine = machines[0].machine_name;
                this.logger.log('info', `Loading diagram for ${firstMachine}`);
                await this.diagramManager.loadDiagram(firstMachine);
            } else {
                this.logger.log('warning', 'No machines found to display diagram');
            }
        } catch (error) {
            this.logger.log('error', `Failed to load initial diagram: ${error.message}`);
        }
    }

    initializeUI() {
        // Get DOM elements
        this.machinesContainer = document.getElementById('machines-container');
        this.totalMachinesEl = document.getElementById('total-machines');
        this.activeMachinesEl = document.getElementById('active-machines');
        this.lastUpdateEl = document.getElementById('last-update');
        this.activityLog = document.getElementById('activity-log');
        this.diagramContainer = document.getElementById('fsm-diagram');
        this.breadcrumbNav = document.querySelector('.breadcrumb-nav');
    }

    initializeModules() {
        // Activity Logger
        this.logger = new ActivityLogger(this.activityLog);
        this.logger.log('info', 'State Machine Monitor initialized');

        // Machine State Manager
        this.machineManager = new MachineStateManager(
            this.machinesContainer,
            {
                total: this.totalMachinesEl,
                active: this.activeMachinesEl,
                lastUpdate: this.lastUpdateEl
            },
            this.logger
        );

        // Diagram Manager
        this.diagramManager = new DiagramManager(
            this.diagramContainer,
            this.breadcrumbNav,
            this.logger
        );

        // WebSocket Manager with event handlers
        this.wsManager = new WebSocketManager({
            initial: (data) => {
                this.logger.log('info', 'Received initial state snapshot');
                if (data.machines) {
                    this.machineManager.updateMachines(data.machines);
                }
            },
            state_change: (data) => {
                const { machine, transition } = this.machineManager.handleStateChange(data);
                
                // Update diagram if this is the selected machine
                if (data.machine_name === this.diagramManager.selectedMachine) {
                    this.diagramManager.updateState(
                        machine.current_state,
                        transition
                    );
                }
            },
            activity_log: (data) => {
                // Handle activity log events from state machine
                const payload = data.payload || {};
                const level = payload.level || 'info';
                const message = payload.message || 'Activity log';
                this.logger.log(level, `[${data.machine_name}] ${message}`);
            },
            job_started: (data) => {
                this.logger.logJobStarted(data);
            },
            job_completed: (data) => {
                this.logger.logJobCompleted(data);
            },
            error: (data) => {
                this.logger.logError(data);
            },
            log: (level, message) => {
                this.logger.log(level, message);
            }
        });
    }

    initializeDiagramTabs() {
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                // Update active state
                tabButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');

                // Load diagram for selected machine
                const machineName = button.getAttribute('data-machine');
                this.diagramManager.loadDiagram(machineName).then(() => {
                    // State is now automatically restored from localStorage in loadDiagram
                    // No need to manually call updateState here
                    console.log(`[App] Switched to ${machineName} diagram`);
                });
            });
        });
    }

    destroy() {
        this.wsManager.destroy();
    }
}

// Initialize monitor when page loads
let monitor;

document.addEventListener('DOMContentLoaded', () => {
    monitor = new StateMachineMonitor();
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (monitor) {
        monitor.destroy();
    }
});

// Export for debugging
window.monitor = monitor;
