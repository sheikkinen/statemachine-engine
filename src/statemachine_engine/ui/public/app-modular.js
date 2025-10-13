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
        
        // Start connections
        this.wsManager.connect();
    }

    createDiagramTabs(machines) {
        const tabsContainer = document.getElementById('diagram-tabs');
        if (!tabsContainer) {
            console.error('diagram-tabs container not found');
            return;
        }

        tabsContainer.innerHTML = '';

        if (machines.length === 0) {
            tabsContainer.innerHTML = '<div class="no-machines">No machines running. Start a machine to see diagrams.</div>';
            return;
        }

        machines.forEach((machine, index) => {
            const button = document.createElement('button');
            button.className = 'tab-button';
            if (index === 0) {
                button.classList.add('active');
            }
            button.setAttribute('data-machine', machine.machine_name);
            button.textContent = machine.machine_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

            button.addEventListener('click', () => {
                // Update active state
                document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');

                // Load diagram for selected machine
                this.diagramManager.loadDiagram(machine.machine_name).then(() => {
                    console.log(`[App] Switched to ${machine.machine_name} diagram`);
                });
            });

            tabsContainer.appendChild(button);
        });

        this.logger.log('success', `Created ${machines.length} diagram tab(s)`);
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
                    
                    // Create tabs for all machines
                    this.createDiagramTabs(data.machines);
                    
                    // Load diagram for first machine
                    if (data.machines.length > 0) {
                        const firstMachine = data.machines[0].machine_name;
                        this.logger.log('info', `Loading diagram for ${firstMachine}`);
                        this.diagramManager.loadDiagram(firstMachine);
                    }
                }
            },
            state_change: (data) => {
                const timestamp = Date.now();
                console.log(`[App] ${timestamp} - Processing state_change event:`, data);
                
                const { machine, transition } = this.machineManager.handleStateChange(data);
                
                console.log(`[App] ${timestamp} - Extracted machine:`, machine);
                console.log(`[App] ${timestamp} - Extracted transition:`, transition);
                
                // Update diagram if this is the selected machine
                if (data.machine_name === this.diagramManager.selectedMachine) {
                    console.log(`[App] ${timestamp} - Updating diagram for selected machine: ${data.machine_name}`);
                    this.diagramManager.updateState(
                        machine.current_state,
                        transition
                    );
                } else {
                    console.log(`[App] ${timestamp} - Skipping diagram update - not selected machine (${data.machine_name} vs ${this.diagramManager.selectedMachine})`);
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
