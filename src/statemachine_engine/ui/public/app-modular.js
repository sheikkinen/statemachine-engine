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
        this.initializeUI();
        this.initializeModules();
        
        // Start connections
        this.initializeConnections();
    }

    async initializeConnections() {
        await this.wsManager.connect();
    }

    // Check if machine should use Kanban view (templated) or Diagram view (unique)
    isKanbanMachine(config_type) {
        const metadata = this.diagramManager.configMetadata.get(config_type);
        return metadata?.template === true;
    }

    // Show Kanban view, hide diagram
    showKanban() {
        this.kanbanContainer.style.display = 'block';
        this.diagramContainer.style.display = 'none';
        this.breadcrumbNav.style.display = 'none';
        console.log('[App] Switched to Kanban view');
    }

    // Show Diagram view, hide Kanban
    showDiagram() {
        this.diagramContainer.style.display = 'block';
        this.breadcrumbNav.style.display = 'block';
        this.kanbanContainer.style.display = 'none';
        console.log('[App] Switched to Diagram view');
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

            button.addEventListener('click', async () => {
                // Update active state
                document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');

                // Load diagram or show kanban based on machine type
                const diagramType = machine.config_type || machine.machine_name;
                
                // Ensure metadata is loaded before checking template flag
                if (!this.diagramManager.configMetadata.has(diagramType)) {
                    console.log(`[App] Fetching metadata for ${diagramType}...`);
                    await this.diagramManager.fetchConfigMetadata(diagramType);
                }
                
                if (this.isKanbanMachine(diagramType)) {
                    console.log(`[App] ${machine.machine_name} is a template - showing Kanban view`);
                    // Set selectedMachine so rebuildKanbanView knows which config to use
                    this.diagramManager.selectedMachine = diagramType;
                    // Also need to load the metadata for state groups
                    await this.diagramManager.loadDiagram(diagramType);
                    this.showKanban();
                    this.rebuildKanbanView();
                } else {
                    console.log(`[App] ${machine.machine_name} is unique - showing Diagram view`);
                    this.showDiagram();
                    this.diagramManager.loadDiagram(diagramType).then(() => {
                        console.log(`[App] Loaded diagram for ${machine.machine_name} (type: ${diagramType})`);
                    });
                }
            });

            tabsContainer.appendChild(button);
        });

        this.logger.log('success', `Created ${machines.length} diagram tab(s)`);
    }
    
    rebuildKanbanView() {
        // If no machines, nothing to show
        if (!this.machineManager || !this.machineManager.machines || this.machineManager.machines.size === 0) {
            console.log('[Kanban] No machines available for Kanban view');
            return;
        }

        // Get ALL states from the diagram configuration, not just from current machines
        const templateName = this.diagramManager.selectedMachine || 'all-machines';
        let states = null;
        let stateGroups = null;
        
        if (this.diagramManager.selectedMachine && this.diagramManager.stateGroupManager) {
            // Get all states from FSM configuration
            states = this.diagramManager.stateGroupManager.getStates('main');
            // Get state groups from diagram if available
            stateGroups = this.diagramManager.getStateGroups();
        }
        
        // Fallback: collect states from current machines if config not available
        if (!states || states.length === 0) {
            console.log('[Kanban] No states from config, collecting from machines');
            const allStates = new Set();
            this.machineManager.machines.forEach(machine => {
                if (machine.current_state) {
                    allStates.add(machine.current_state);
                }
            });
            states = Array.from(allStates);
        }

        if (states.length === 0) {
            console.log('[Kanban] No states found');
            return;
        }

        console.log(`[Kanban] Rebuilding view for template: ${templateName}`);
        console.log(`[Kanban] States from config:`, states);
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

        // Add ALL machines to Kanban view
        this.machineManager.machines.forEach(machine => {
            console.log(`[Kanban] Adding card for ${machine.machine_name} in state ${machine.current_state}`);
            this.kanbanView.addCard(machine.machine_name, machine.current_state);
        });
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

                    // Load first machine's view (diagram or kanban based on type)
                    if (data.machines.length > 0) {
                        const firstMachine = data.machines[0];
                        const diagramType = firstMachine.config_type || firstMachine.machine_name;
                        
                        // Need to fetch metadata first for view routing
                        this.diagramManager.fetchConfigMetadata(diagramType).then(() => {
                            if (this.isKanbanMachine(diagramType)) {
                                this.logger.log('info', `First machine is templated - showing Kanban view`);
                                this.showKanban();
                                this.rebuildKanbanView();
                            } else {
                                this.logger.log('info', `Loading diagram for ${firstMachine.machine_name} (type: ${diagramType})`);
                                this.showDiagram();
                                this.diagramManager.loadDiagram(diagramType);
                                this.rebuildKanbanView(); // Still build kanban in background
                            }
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
                
                // Update Kanban view if Kanban is currently visible
                if (this.kanbanView && this.kanbanContainer.style.display !== 'none') {
                    console.log(`[App] ${timestamp} - Updating Kanban card for ${data.machine_name}`);
                    // Check if card exists, if not add it
                    if (!this.kanbanView.cards[data.machine_name]) {
                        this.kanbanView.addCard(data.machine_name, machine.current_state);
                    } else {
                        this.kanbanView.updateCard(data.machine_name, machine.current_state);
                    }
                }
                
                // Update diagram if visible and this machine's config_type matches selected diagram
                const machineConfigType = machine.config_type || data.machine_name;
                if (this.diagramContainer.style.display !== 'none' && 
                    machineConfigType === this.diagramManager.selectedMachine) {
                    console.log(`[App] ${timestamp} - Updating diagram for machine: ${data.machine_name} (type: ${machineConfigType})`);
                    this.diagramManager.updateState(
                        machine.current_state,
                        transition
                    );
                } else {
                    console.log(`[App] ${timestamp} - Skipping diagram update - wrong type or not visible (machine ${data.machine_name} type ${machineConfigType} vs selected ${this.diagramManager.selectedMachine})`);
                }
            },
            machine_registered: async (data) => {
                // Handle new machine registration (Option 4: Event + Lazy Loading)
                console.log(`[App] Machine registered:`, data);

                // Extract from payload (event structure: {type, machine_name, payload: {config_type, current_state, ...}})
                const machine_name = data.machine_name || data.payload?.machine_name;
                const config_type = data.payload?.config_type;
                const current_state = data.payload?.current_state;

                // Log to activity log immediately
                this.logger.log('success', `📥 Machine registered: ${machine_name} (${config_type}) - state: ${current_state}`);

                // Validate config_type exists
                if (!config_type) {
                    console.warn(`[App] machine_registered event missing config_type for ${machine_name}`);
                    this.logger.log('warning', `⚠️ machine_registered event missing config_type for ${machine_name}`);
                    return;
                }

                // Check if this is the first machine
                const isFirstMachine = this.machineManager.machines.size === 0;

                // Add to machine manager
                this.machineManager.machines.set(machine_name, {
                    machine_name,
                    config_type,
                    current_state,
                    last_activity: data.payload?.timestamp || Date.now() / 1000
                });

                // Render the machine card in the UI
                this.machineManager.renderMachines();
                console.log(`[App] Created machine card for: ${machine_name}`);

                // Rebuild diagram tabs to include new machine
                const allMachines = Array.from(this.machineManager.machines.values());
                this.createDiagramTabs(allMachines);

                // Check if we have metadata for this config type
                if (!this.diagramManager.hasConfig(config_type)) {
                    console.log(`[App] New config type detected: ${config_type}, fetching metadata...`);
                    const metadata = await this.diagramManager.fetchConfigMetadata(config_type);

                    if (metadata) {
                        this.logger.log('success', `✓ Loaded metadata for ${config_type}`);
                    } else {
                        this.logger.log('warning', `⚠️ Failed to load metadata for ${config_type}`);
                    }
                } else {
                    console.log(`[App] Config type ${config_type} already loaded`);
                }

                // If this is the first machine, load its view (diagram or kanban)
                if (isFirstMachine) {
                    console.log(`[App] First machine registered: ${machine_name}`);
                    
                    if (this.isKanbanMachine(config_type)) {
                        this.logger.log('info', `First machine is templated - showing Kanban view`);
                        this.showKanban();
                        this.rebuildKanbanView();
                    } else {
                        this.logger.log('info', `Loading diagram for ${machine_name} (type: ${config_type})`);
                        this.showDiagram();
                        this.diagramManager.loadDiagram(config_type);
                    }
                }

                // Add to Kanban view if Kanban is currently visible
                if (this.kanbanContainer.style.display !== 'none' && this.kanbanView) {
                    console.log(`[App] Adding machine to Kanban: ${machine_name}`);
                    this.kanbanView.addCard(machine_name, current_state);
                }
            },
            machine_terminated: (data) => {
                // Handle machine termination
                console.log(`[App] Machine terminated:`, data);

                // Extract machine_name (may be at top level or in payload)
                const machine_name = data.machine_name || data.payload?.machine_name;

                // Log to activity log immediately
                this.logger.log('info', `📤 Machine terminated: ${machine_name}`);

                // Remove from machine manager
                this.machineManager.machines.delete(machine_name);

                // Render machines to remove the card from UI
                this.machineManager.renderMachines();
                console.log(`[App] Removed machine card for: ${machine_name}`);

                // Rebuild diagram tabs to remove terminated machine
                const allMachines = Array.from(this.machineManager.machines.values());
                this.createDiagramTabs(allMachines);

                // Remove from Kanban if Kanban is currently visible
                if (this.kanbanContainer.style.display !== 'none' && this.kanbanView) {
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
