/**
 * Main Application - State Machine Monitor
 * Orchestrates all modules for real-time state machine monitoring
 */

import { WebSocketManager } from './modules/WebSocketManager.js';
import { DiagramManager } from './modules/DiagramManager.js';
import { MachineStateManager } from './modules/MachineStateManager.js';
import { ActivityLogger } from './modules/ActivityLogger.js';
import KanbanView from './modules/KanbanView.js';

class StateMachineMonitor {
    constructor() {
        this.kanbanView = null;
        this.kanbanVisible = false;
        this.initializeUI();
        this.initializeModules();
        
        // Start connections
        this.initializeConnections();
    }

    async initializeConnections() {
        await this.wsManager.connect();
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
            // Hide Kanban toggle if no machines
            if (this.kanbanToggleBtn) {
                this.kanbanToggleBtn.style.display = 'none';
            }
            return;
        }
        
        // Show Kanban toggle button when machines are available
        if (this.kanbanToggleBtn) {
            this.kanbanToggleBtn.style.display = 'inline-block';
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

                // Load diagram for selected machine (use config_type if available)
                const diagramType = machine.config_type || machine.machine_name;
                this.diagramManager.loadDiagram(diagramType).then(() => {
                    console.log(`[App] Switched to ${machine.machine_name} diagram (type: ${diagramType})`);
                    // Rebuild Kanban view for new template
                    this.rebuildKanbanView();
                });
            });

            tabsContainer.appendChild(button);
        });

        this.logger.log('success', `Created ${machines.length} diagram tab(s)`);
    }
    
    toggleKanbanView() {
        this.kanbanVisible = !this.kanbanVisible;
        
        if (this.kanbanVisible) {
            // Show Kanban, hide diagram
            this.diagramContainer.style.display = 'none';
            this.breadcrumbNav.style.display = 'none';
            if (this.kanbanView) {
                this.kanbanView.show();
            }
            this.kanbanToggleBtn.textContent = 'Show Diagram';
            this.kanbanToggleBtn.classList.add('active');
        } else {
            // Show diagram, hide Kanban
            this.diagramContainer.style.display = '';
            this.breadcrumbNav.style.display = '';
            if (this.kanbanView) {
                this.kanbanView.hide();
            }
            this.kanbanToggleBtn.textContent = 'Show Kanban View';
            this.kanbanToggleBtn.classList.remove('active');
        }
    }
    
    rebuildKanbanView() {
        // Get states from current diagram
        const states = this.diagramManager.getStates();
        if (!states || states.length === 0) {
            console.log('[Kanban] No states available for Kanban view');
            return;
        }
        
        // Get state groups (if available)
        const stateGroups = this.diagramManager.getStateGroups();
        
        const templateName = this.diagramManager.selectedMachine;
        console.log(`[Kanban] Rebuilding view for template: ${templateName}`);
        console.log(`[Kanban] States:`, states);
        console.log(`[Kanban] State groups:`, stateGroups);
        
        // Create or recreate Kanban view
        this.kanbanView = new KanbanView(
            this.kanbanContainer,
            templateName,
            states,
            this.logger,
            stateGroups  // Pass state groups (null for flat view)
        );
        this.kanbanView.render();
        
        // Add CSS class for grouped display
        if (stateGroups) {
            this.kanbanContainer.classList.add('grouped');
        } else {
            this.kanbanContainer.classList.remove('grouped');
        }
        
        // Add all current machines matching this template
        if (this.machineManager && this.machineManager.machines) {
            this.machineManager.machines.forEach(machine => {
                const machineType = machine.config_type || machine.machine_name;
                if (machineType === templateName) {
                    console.log(`[Kanban] Adding card for ${machine.machine_name} in state ${machine.current_state}`);
                    this.kanbanView.addCard(machine.machine_name, machine.current_state);
                }
            });
        }
        
        // Keep visibility state
        if (this.kanbanVisible) {
            this.kanbanView.show();
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
        this.kanbanContainer = document.getElementById('kanban-container');
        this.kanbanToggleBtn = document.getElementById('kanban-toggle');
        
        // Set up Kanban toggle button
        if (this.kanbanToggleBtn) {
            this.kanbanToggleBtn.addEventListener('click', () => {
                this.toggleKanbanView();
            });
        }
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
                        const firstMachine = data.machines[0];
                        const diagramType = firstMachine.config_type || firstMachine.machine_name;
                        this.logger.log('info', `Loading diagram for ${firstMachine.machine_name} (type: ${diagramType})`);
                        this.diagramManager.loadDiagram(diagramType).then(() => {
                            // Build Kanban view after diagram loads
                            this.rebuildKanbanView();
                        });
                    }
                }
            },
            state_change: (data) => {
                const timestamp = Date.now();
                console.log(`[App] ${timestamp} - Processing state_change event:`, data);
                
                const { machine, transition } = this.machineManager.handleStateChange(data);
                
                console.log(`[App] ${timestamp} - Extracted machine:`, machine);
                console.log(`[App] ${timestamp} - Extracted transition:`, transition);
                
                // Update diagram if this machine's config_type matches the selected diagram
                // Use config_type from the machine object (which has the template name)
                const machineConfigType = machine.config_type || data.machine_name;
                if (machineConfigType === this.diagramManager.selectedMachine) {
                    console.log(`[App] ${timestamp} - Updating diagram for machine: ${data.machine_name} (type: ${machineConfigType})`);
                    this.diagramManager.updateState(
                        machine.current_state,
                        transition
                    );
                    
                    // Update Kanban view if visible
                    if (this.kanbanView && this.kanbanVisible) {
                        console.log(`[App] ${timestamp} - Updating Kanban card for ${data.machine_name}`);
                        // Check if card exists, if not add it
                        if (!this.kanbanView.cards[data.machine_name]) {
                            this.kanbanView.addCard(data.machine_name, machine.current_state);
                        } else {
                            this.kanbanView.updateCard(data.machine_name, machine.current_state);
                        }
                    }
                } else {
                    console.log(`[App] ${timestamp} - Skipping diagram update - wrong type (machine ${data.machine_name} type ${machineConfigType} vs selected ${this.diagramManager.selectedMachine})`);
                }
            },
            machine_registered: async (data) => {
                // Handle new machine registration (Option 4: Event + Lazy Loading)
                console.log(`[App] Machine registered:`, data);
                const { machine_name, config_type, current_state } = data;
                
                // Check if we have metadata for this config type
                if (!this.diagramManager.hasConfig(config_type)) {
                    console.log(`[App] New config type detected: ${config_type}, fetching metadata...`);
                    const metadata = await this.diagramManager.fetchConfigMetadata(config_type);
                    
                    if (metadata) {
                        this.logger.log('success', `✓ Loaded metadata for ${config_type}`);
                        
                        // If Kanban view is visible, refresh it to include new machine
                        if (this.kanbanVisible && this.kanbanView) {
                            console.log(`[App] Adding machine to Kanban: ${machine_name}`);
                            this.kanbanView.addCard(machine_name, current_state);
                        }
                    } else {
                        this.logger.log('warning', `⚠️ Failed to load metadata for ${config_type}`);
                    }
                } else {
                    console.log(`[App] Config type ${config_type} already loaded`);
                }
            },
            machine_terminated: (data) => {
                // Handle machine termination
                console.log(`[App] Machine terminated:`, data);
                const { machine_name } = data;
                
                // Remove from Kanban if visible
                if (this.kanbanVisible && this.kanbanView) {
                    console.log(`[App] Removing machine from Kanban: ${machine_name}`);
                    this.kanbanView.removeCard(machine_name);
                }
                
                this.logger.log('info', `👋 Machine terminated: ${machine_name}`);
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

// Debugging helpers for SVG enrichment
window.checkSvgEnrichment = () => {
    if (monitor && monitor.diagramManager) {
        monitor.diagramManager.checkSvgEnrichment();
    } else {
        console.log('Monitor not initialized');
    }
};

window.forceReEnrich = () => {
    if (monitor && monitor.diagramManager) {
        monitor.diagramManager.forceReEnrich();
    } else {
        console.log('Monitor not initialized');
    }
};

window.clearDiagramCache = () => {
    if (monitor && monitor.diagramManager) {
        const container = monitor.diagramManager.container;
        container.dataset.enriched = 'false';
        console.log('[Debug] Cleared enrichment flag - next update will re-render');
    } else {
        console.log('Monitor not initialized');
    }
};
