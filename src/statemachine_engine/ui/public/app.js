class StateMachineMonitor {
    constructor() {
        this.machines = new Map();
        this.websocket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectDelay = 30000; // 30 seconds
        this.currentDiagram = null;
        this.selectedMachine = null;
        this.currentState = null;
        this.pingInterval = null;
        this.lastTransitions = new Map(); // Track last transition per machine

        this.initializeUI();
        this.connectWebSocket();
        this.initializeFromAPI(); // Load machines and create tabs dynamically
    }

    initializeUI() {
        // Get DOM elements
        this.machinesContainer = document.getElementById('machines-container');
        this.totalMachinesEl = document.getElementById('total-machines');
        this.activeMachinesEl = document.getElementById('active-machines');
        this.lastUpdateEl = document.getElementById('last-update');
        this.activityLog = document.getElementById('activity-log');
        this.diagramContainer = document.getElementById('fsm-diagram');

        this.logActivity('info', 'State Machine Monitor initialized');
    }

    async initializeFromAPI() {
        try {
            // Fetch machines from API
            const response = await fetch('/api/machines');
            if (!response.ok) {
                throw new Error(`Failed to fetch machines: ${response.statusText}`);
            }

            const machines = await response.json();

            // Create tabs dynamically
            const tabsContainer = document.getElementById('diagram-tabs');
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
                    this.selectedMachine = machine.machine_name;
                }
                button.setAttribute('data-machine', machine.machine_name);
                button.textContent = machine.machine_name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

                button.addEventListener('click', () => {
                    // Update active state
                    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
                    button.classList.add('active');

                    // Load diagram for selected machine
                    this.selectedMachine = machine.machine_name;
                    this.currentState = null;

                    this.loadDiagram(machine.machine_name).then(() => {
                        const machineData = this.machines.get(machine.machine_name);
                        if (machineData && machineData.current_state) {
                            this.renderDiagram(machineData.current_state);
                        }
                    });
                });

                tabsContainer.appendChild(button);
            });

            // Load first machine's diagram
            if (machines.length > 0 && this.selectedMachine) {
                await this.loadDiagram(this.selectedMachine);
            }

        } catch (error) {
            this.logActivity('error', `Failed to initialize from API: ${error.message}`);
            console.error('Initialization error:', error);
        }
    }

    async loadDiagram(machineName) {
        try {
            this.logActivity('info', `Loading diagram for ${machineName}...`);

            const response = await fetch(`/api/diagram/${machineName}`);
            if (!response.ok) {
                throw new Error(`Failed to load diagram: ${response.statusText}`);
            }

            const data = await response.json();
            this.currentDiagram = data.diagram;

            await this.renderDiagram();

            this.logActivity('success', `Diagram loaded for ${machineName}`);
        } catch (error) {
            this.logActivity('error', `Failed to load diagram: ${error.message}`);
            this.diagramContainer.innerHTML = `
                <div class="error">
                    <p>❌ Failed to load diagram</p>
                    <p class="error-detail">${error.message}</p>
                </div>
            `;
        }
    }

    async renderDiagram(highlightState = null, transition = null) {
        if (!this.currentDiagram) return;

        try {
            let diagramCode = this.currentDiagram;

            // Add CSS styling for active state if provided
            if (highlightState) {
                console.log(`Rendering diagram with highlighted state: ${highlightState}`);
                diagramCode += `\n\n    classDef active fill:#90EE90,stroke:#006400,stroke-width:4px`;
                diagramCode += `\n    class ${highlightState} active`;
            }

            // Log transition info for debugging
            if (transition) {
                console.log(`Transition: ${transition.from} → ${transition.to} (${transition.event})`);
            }

            // Add redrawing class for fade effect
            this.diagramContainer.classList.add('redrawing');

            // Small delay to allow fade-out effect to be visible
            await new Promise(resolve => setTimeout(resolve, 50));

            // Clear container and render new diagram
            this.diagramContainer.innerHTML = `<pre class="mermaid">${diagramCode}</pre>`;

            // Render with Mermaid
            const mermaidEl = this.diagramContainer.querySelector('.mermaid');
            await window.mermaid.run({ nodes: [mermaidEl] });

            // Mark container as having diagram (prevents height collapse)
            this.diagramContainer.classList.add('has-diagram');

            // Remove redrawing class to fade back in
            this.diagramContainer.classList.remove('redrawing');

            // Highlight transition arrow if provided
            if (transition && transition.from && transition.to) {
                setTimeout(() => {
                    this.highlightTransitionArrow(transition.from, transition.to);
                }, 100); // Wait for Mermaid render to complete
            }
        } catch (error) {
            console.error('Error rendering diagram:', error);
            this.logActivity('error', `Diagram rendering failed: ${error.message}`);
            this.diagramContainer.classList.remove('redrawing');
        }
    }

    connectWebSocket() {
        this.logActivity('info', 'Connecting to WebSocket server...');

        try {
            this.websocket = new WebSocket('ws://localhost:3002/ws/events');

            this.websocket.onopen = () => {
                this.isConnected = true;
                this.logActivity('success', '✓ WebSocket connection established');
                this.reconnectAttempts = 0;

                // Start heartbeat ping
                this.startPingInterval();
            };

            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.debug('WebSocket message received:', data);
                    this.handleWebSocketEvent(data);
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e, 'Raw data:', event.data);
                }
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.logActivity('error', 'WebSocket error occurred');
            };

            this.websocket.onclose = () => {
                this.isConnected = false;
                this.stopPingInterval();
                this.logActivity('warning', 'WebSocket disconnected. Reconnecting...');
                this.scheduleReconnect();
            };
        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.logActivity('error', `Connection failed: ${error.message}`);
            this.scheduleReconnect();
        }
    }

    handleWebSocketEvent(data) {
        // Route events based on type
        switch(data.type) {
            case 'initial':
                // Full state snapshot on connect
                this.logActivity('info', 'Received initial state snapshot');
                if (data.machines) {
                    this.updateMachines(data.machines);
                }
                break;

            case 'state_change':
                // Real-time state change from state machine
                this.handleStateChange(data);
                break;

            case 'job_started':
                this.handleJobStarted(data);
                break;

            case 'job_completed':
                this.handleJobCompleted(data);
                break;

            case 'error':
                this.handleErrorEvent(data);
                break;

            case 'pong':
                // Heartbeat response
                console.debug('Received pong');
                break;

            default:
                console.warn('Unknown event type:', data.type, 'Full event:', data);
        }
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
            // Machine not in initial state - create new entry
            machine = {
                machine_name: machineName,
                current_state: payload.to_state,
                last_activity: payload.timestamp || Date.now() / 1000,
                running: true,  // If it's sending events, it's running
                metadata: null
            };
            this.machines.set(machineName, machine);
            
            // Re-render all machines to include the new one
            this.renderMachines();
            
            this.logActivity('info', `New machine detected: ${machineName}`);
        } else {
            // Update existing machine
            machine.current_state = payload.to_state;
            machine.last_activity = payload.timestamp || Date.now() / 1000;
            machine.running = true;  // If it's sending events, it's running
            this.machines.set(machineName, machine);
            
            // Update machine card
            this.updateMachineCard(machine);
        }
        
        // Update diagram if this is the selected machine
        if (machineName === this.selectedMachine) {
            const transition = this.lastTransitions.get(machineName);
            this.updateDiagramState(payload.to_state, transition);
        }
        
        // Log transition
        if (payload.from_state && payload.to_state) {
            this.logActivity('info', 
                `${machineName}: ${payload.from_state} → ${payload.to_state}`);
        }
    }

    handleJobStarted(data) {
        const machineName = data.machine_name;
        const payload = data.payload || {};
        const jobId = payload.job_id || 'unknown';
        
        this.logActivity('info', `${machineName}: Job ${jobId} started`);
    }

    handleJobCompleted(data) {
        const machineName = data.machine_name;
        const payload = data.payload || {};
        const jobId = payload.job_id || 'unknown';
        
        this.logActivity('success', `${machineName}: Job ${jobId} completed`);
    }

    handleErrorEvent(data) {
        const machineName = data.machine_name;
        const payload = data.payload || {};
        const errorMessage = payload.error_message || 'Unknown error';
        const jobId = payload.job_id;
        
        const message = jobId ? 
            `${machineName}: Error in job ${jobId}: ${errorMessage}` :
            `${machineName}: ${errorMessage}`;
        
        this.logActivity('error', message);
    }

    startPingInterval() {
        // Send ping every 30 seconds to keep connection alive
        this.pingInterval = setInterval(() => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send('ping');
            }
        }, 30000);
    }

    stopPingInterval() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    scheduleReconnect() {
        // Close existing connection
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }

        // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (max)
        const delay = Math.min(
            1000 * Math.pow(2, this.reconnectAttempts),
            this.maxReconnectDelay
        );

        this.reconnectAttempts++;

        this.logActivity('info', `Reconnecting in ${delay/1000}s...`);

        setTimeout(() => {
            this.connectWebSocket();
        }, delay);
    }

    updateMachines(machines) {
        // Update machines map
        this.machines.clear();
        machines.forEach(machine => {
            this.machines.set(machine.machine_name, machine);
        });

        // Update status bar
        const activeMachines = machines.filter(m => m.running).length;
        this.totalMachinesEl.textContent = machines.length;
        this.activeMachinesEl.textContent = activeMachines;
        this.lastUpdateEl.textContent = new Date().toLocaleTimeString();

        // Render machine cards
        this.renderMachines();

        // Update diagram for selected machine if state changed
        const selectedMachine = this.machines.get(this.selectedMachine);
        if (selectedMachine && selectedMachine.current_state) {
            this.updateDiagramState(selectedMachine.current_state);
        }
    }

    updateMachineCard(machine) {
        // Find existing card and update it
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

    updateDiagramState(currentState, transition = null) {
        // Only re-render if state changed
        if (this.currentState === currentState) return;

        const previousState = this.currentState;
        this.currentState = currentState;

        // Log state transition
        if (previousState) {
            this.logActivity('info', `${this.selectedMachine}: ${previousState} → ${currentState}`);
        }

        this.renderDiagram(currentState, transition);
    }

    highlightTransitionArrow(fromState, toState) {
        console.log(`[Arrow Highlight] Looking for transition: ${fromState} → ${toState}`);
        console.log(`[Arrow Highlight] Current selected machine: ${this.selectedMachine}`);
        
        const svg = this.diagramContainer.querySelector('svg');
        if (!svg) {
            console.warn('[Arrow Highlight] No SVG found in diagram container');
            return;
        }

        // Find all edge paths - Mermaid v11 uses paths with class containing "edge" and "transition"
        const edges = svg.querySelectorAll('path[class*="edge"][class*="transition"]');
        console.log(`[Arrow Highlight] Found ${edges.length} edge paths`);
        
        if (edges.length === 0) {
            console.log('[Arrow Highlight] No edges found');
            return;
        }
        
        // Find nodes by state name pattern: state-{stateName}-{number}
        const fromNodePattern = `state-${fromState}-`;
        const toNodePattern = `state-${toState}-`;
        
        const allNodes = svg.querySelectorAll('g.node');
        let fromNode = null;
        let toNode = null;
        
        // Debug: log all node IDs
        const nodeIds = Array.from(allNodes).map(n => n.id);
        console.log(`[Arrow Highlight] All node IDs:`, nodeIds);
        console.log(`[Arrow Highlight] Looking for patterns: "${fromNodePattern}" and "${toNodePattern}"`);
        
        allNodes.forEach(node => {
            if (node.id.startsWith(fromNodePattern)) {
                fromNode = node;
                console.log(`[Arrow Highlight] ✓ Found from node: ${node.id}`);
            }
            if (node.id.startsWith(toNodePattern)) {
                toNode = node;
                console.log(`[Arrow Highlight] ✓ Found to node: ${node.id}`);
            }
        });
        
        if (!fromNode || !toNode) {
            console.log(`[Arrow Highlight] ❌ Could not find both nodes (from: ${!!fromNode}, to: ${!!toNode})`);
            console.log(`[Arrow Highlight] This might be a cross-machine transition or the states don't exist in this diagram`);
            return;
        }
        
        console.log(`[Arrow Highlight] Found nodes: ${fromNode.id} → ${toNode.id}`);
        
        // Check for self-loop first (special case with state name in edge ID)
        const isSelfLoop = fromState === toState;
        if (isSelfLoop) {
            const cyclic = svg.querySelector(`path[id*="${fromState}-cyclic-special"]`);
            if (cyclic) {
                console.log(`[Arrow Highlight] ✓ Found self-loop: ${cyclic.id}`);
                cyclic.classList.add('last-transition-arrow');
                
                setTimeout(() => {
                    cyclic.classList.remove('last-transition-arrow');
                    cyclic.classList.add('fading');
                    setTimeout(() => cyclic.classList.remove('fading'), 500);
                }, 2000);
                return;
            }
        }
        
        // Get node positions in SVG coordinate system
        // Use getCTM() to get the actual transformation matrix
        const fromCTM = fromNode.getCTM();
        const toCTM = toNode.getCTM();
        const fromBBox = fromNode.getBBox();
        const toBBox = toNode.getBBox();
        
        // Calculate center in SVG coordinates using CTM
        const svgPoint = svg.createSVGPoint();
        
        // From node center
        svgPoint.x = fromBBox.x + fromBBox.width / 2;
        svgPoint.y = fromBBox.y + fromBBox.height / 2;
        const fromTransformed = svgPoint.matrixTransform(fromCTM);
        
        // To node center
        svgPoint.x = toBBox.x + toBBox.width / 2;
        svgPoint.y = toBBox.y + toBBox.height / 2;
        const toTransformed = svgPoint.matrixTransform(toCTM);
        
        const fromCenter = { x: fromTransformed.x, y: fromTransformed.y };
        const toCenter = { x: toTransformed.x, y: toTransformed.y };
        
        console.log(`[Arrow Highlight] From center: (${fromCenter.x.toFixed(1)}, ${fromCenter.y.toFixed(1)})`);
        console.log(`[Arrow Highlight] To center: (${toCenter.x.toFixed(1)}, ${toCenter.y.toFixed(1)})`);
        
        // SIMPLIFIED APPROACH: Find edge by node ordering
        // Edges are created in the order they appear in the state machine definition
        // We'll find the edge that connects these two nodes by checking which edge
        // is between the two node positions
        
        let bestMatch = null;
        let bestScore = Infinity;
        
        console.log(`[Arrow Highlight] Processing ${edges.length} edges...`);
        
        edges.forEach((edge, idx) => {
            const pathData = edge.getAttribute('d');
            if (!pathData) return;
            
            // Extract start and end coordinates
            const startMatch = pathData.match(/M\s*([\d.]+)[,\s]+([\d.]+)/);
            if (!startMatch) return;
            
            const startX = parseFloat(startMatch[1]);
            const startY = parseFloat(startMatch[2]);
            
            // Get all coordinate pairs to find the end
            const coordPairs = pathData.match(/([\d.]+)[,\s]+([\d.]+)/g);
            if (!coordPairs || coordPairs.length === 0) return;
            
            const lastPair = coordPairs[coordPairs.length - 1];
            const lastMatch = lastPair.match(/([\d.]+)[,\s]+([\d.]+)/);
            if (!lastMatch) return;
            
            const endX = parseFloat(lastMatch[1]);
            const endY = parseFloat(lastMatch[2]);
            
            // Calculate midpoint of edge
            const edgeMidX = (startX + endX) / 2;
            const edgeMidY = (startY + endY) / 2;
            
            // Calculate midpoint between nodes
            const nodeMidX = (fromCenter.x + toCenter.x) / 2;
            const nodeMidY = (fromCenter.y + toCenter.y) / 2;
            
            // Score: how close is the edge midpoint to the node midpoint?
            // Plus how well does the edge direction match the node direction?
            const midpointDist = Math.hypot(edgeMidX - nodeMidX, edgeMidY - nodeMidY);
            
            const edgeVector = { x: endX - startX, y: endY - startY };
            const nodeVector = { x: toCenter.x - fromCenter.x, y: toCenter.y - fromCenter.y };
            
            // Dot product to measure alignment
            const dotProduct = edgeVector.x * nodeVector.x + edgeVector.y * nodeVector.y;
            const edgeMag = Math.hypot(edgeVector.x, edgeVector.y);
            const nodeMag = Math.hypot(nodeVector.x, nodeVector.y);
            const alignment = edgeMag > 0 && nodeMag > 0 ? dotProduct / (edgeMag * nodeMag) : 0;
            
            // Good alignment is close to 1 (same direction), bad is close to -1 (opposite)
            const alignmentScore = (1 - alignment) * 100; // Lower is better
            
            const score = midpointDist + alignmentScore;
            
            if (idx < 5 || score < 100) {
                console.log(`[Arrow Highlight] Edge ${idx} (${edge.id}):`);
                console.log(`  Path: (${startX.toFixed(0)}, ${startY.toFixed(0)}) → (${endX.toFixed(0)}, ${endY.toFixed(0)})`);
                console.log(`  Midpoint dist: ${midpointDist.toFixed(1)}, Alignment: ${alignment.toFixed(2)}, Score: ${score.toFixed(1)}`);
            }
            
            if (score < bestScore) {
                bestScore = score;
                bestMatch = edge;
            }
        });
        
        if (bestMatch) {
            console.log(`[Arrow Highlight] ✓ Found matching edge: ${bestMatch.id} (score: ${bestScore.toFixed(1)})`);
            bestMatch.classList.add('last-transition-arrow');
            
            // Remove highlight after 2 seconds with fade animation
            setTimeout(() => {
                bestMatch.classList.remove('last-transition-arrow');
                bestMatch.classList.add('fading');
                setTimeout(() => bestMatch.classList.remove('fading'), 500);
            }, 2000);
        } else {
            console.warn(`[Arrow Highlight] No matching arrow found for ${fromState} → ${toState}`);
            console.log('[Arrow Highlight] Checked', edges.length, 'edges');
            
            // FALLBACK: Try visual approach - find edge that's vertically/horizontally between nodes
            // This works for vertical or horizontal layouts
            const nodeDistance = Math.hypot(toCenter.x - fromCenter.x, toCenter.y - fromCenter.y);
            console.log(`[Arrow Highlight] Node distance: ${nodeDistance.toFixed(1)}px`);
            console.log(`[Arrow Highlight] From: (${fromCenter.x.toFixed(0)}, ${fromCenter.y.toFixed(0)})`);
            console.log(`[Arrow Highlight] To: (${toCenter.x.toFixed(0)}, ${toCenter.y.toFixed(0)})`);
            
            // Try to find edge by order - edges are created in definition order
            // For vertical diagrams, edge from higher Y to lower Y
            const isVertical = Math.abs(toCenter.y - fromCenter.y) > Math.abs(toCenter.x - fromCenter.x);
            console.log(`[Arrow Highlight] Diagram orientation: ${isVertical ? 'vertical' : 'horizontal'}`);
            
            if (isVertical && toCenter.y > fromCenter.y) {
                // Downward transition - find edge whose path goes downward
                const targetDistance = toCenter.y - fromCenter.y;
                console.log(`[Arrow Highlight] Looking for downward edge (target Δy: ${targetDistance.toFixed(0)})`);
                
                let bestCandidate = null;
                let bestScore = Infinity;
                
                for (const edge of edges) {
                    const pathData = edge.getAttribute('d');
                    if (!pathData) continue;
                    
                    // Extract all Y coordinates
                    const yCoords = pathData.match(/,(\d+\.?\d*)/g);
                    const xCoords = pathData.match(/([A-Z]|^)(\d+\.?\d*),/g);
                    
                    if (yCoords && yCoords.length >= 2 && xCoords && xCoords.length >= 2) {
                        const startY = parseFloat(yCoords[0].substring(1));
                        const endY = parseFloat(yCoords[yCoords.length - 1].substring(1));
                        const startX = parseFloat(xCoords[0].replace(/[A-Z]/g, ''));
                        const endX = parseFloat(xCoords[xCoords.length - 1].replace(/[A-Z]/g, ''));
                        
                        const edgeDeltaY = endY - startY;
                        const edgeDeltaX = Math.abs(endX - startX);
                        
                        // Score based on:
                        // 1. How close edgeDeltaY is to targetDistance
                        // 2. Edge should be roughly vertical (small X change)
                        // 3. Edge should start near fromCenter.y
                        const deltaYScore = Math.abs(edgeDeltaY - targetDistance);
                        const horizontalPenalty = edgeDeltaX * 2; // Penalize horizontal movement
                        const startProximity = Math.abs(startY - fromCenter.y);
                        
                        const score = deltaYScore + horizontalPenalty + startProximity;
                        
                        console.log(`[Arrow Highlight]   ${edge.id}: Δy=${edgeDeltaY.toFixed(0)} Δx=${edgeDeltaX.toFixed(0)} start=${startY.toFixed(0)} score=${score.toFixed(1)}`);
                        
                        // Must be downward and reasonable
                        if (edgeDeltaY > 50 && score < bestScore && score < 300) {
                            bestScore = score;
                            bestCandidate = edge;
                        }
                    }
                }
                
                if (bestCandidate) {
                    console.log(`[Arrow Highlight] ✓ Found edge by vertical flow: ${bestCandidate.id} (score: ${bestScore.toFixed(1)})`);
                    bestCandidate.classList.add('last-transition-arrow');
                    setTimeout(() => {
                        bestCandidate.classList.remove('last-transition-arrow');
                        bestCandidate.classList.add('fading');
                        setTimeout(() => bestCandidate.classList.remove('fading'), 500);
                    }, 2000);
                    return;
                }
            }
        }
    }

    renderMachines() {
        this.machinesContainer.innerHTML = '';
        
        this.machines.forEach(machine => {
            const cardEl = this.createMachineCard(machine);
            this.machinesContainer.appendChild(cardEl);
        });
    }

    createMachineCard(machine) {
        const card = document.createElement('div');
        card.className = 'machine-card';
        card.setAttribute('data-machine', machine.machine_name);

        const statusClass = machine.running ? 'running' : 'stopped';
        const statusText = machine.running ? 'Running' : 'Stopped';
        
        // Format last activity time
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
                        onclick="monitor.startMachine('${machine.machine_name}')"
                        ${machine.running ? 'disabled' : ''}>
                    Start
                </button>
                <button class="btn btn-stop" 
                        onclick="monitor.stopMachine('${machine.machine_name}')"
                        ${!machine.running ? 'disabled' : ''}>
                    Stop
                </button>
            </div>
        `;

        return card;
    }

    async startMachine(machineName) {
        try {
            this.logActivity('info', `Starting machine: ${machineName}`);
            
            const response = await fetch(`/api/machine/${machineName}/start`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.logActivity('success', `${result.message} (PID: ${result.pid})`);
            } else {
                this.logActivity('error', `Failed to start ${machineName}: ${result.error}`);
            }
        } catch (error) {
            this.logActivity('error', `Error starting ${machineName}: ${error.message}`);
        }
    }

    async stopMachine(machineName) {
        try {
            this.logActivity('info', `Stopping machine: ${machineName}`);
            
            const response = await fetch(`/api/machine/${machineName}/stop`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.logActivity('success', result.message);
            } else {
                this.logActivity('error', `Failed to stop ${machineName}: ${result.error}`);
            }
        } catch (error) {
            this.logActivity('error', `Error stopping ${machineName}: ${error.message}`);
        }
    }

    updateActivityLog(errors) {
        // Track existing log IDs to avoid duplicates (including all levels: info, success, warning, error)
        const existingErrors = new Set();
        const errorEntries = this.activityLog.querySelectorAll('.log-entry[data-error-id]');
        errorEntries.forEach(entry => {
            existingErrors.add(entry.getAttribute('data-error-id'));
        });

        // Add new log entries to top of log
        errors.forEach(error => {
            // Create unique ID for this log entry (include message to differentiate activity_logs with same timestamp)
            const errorId = `${error.type}_${error.job_id || 'none'}_${error.timestamp}_${(error.message || '').substring(0, 20)}`;

            // Skip if already displayed
            if (existingErrors.has(errorId)) return;

            const entry = document.createElement('div');
            entry.setAttribute('data-error-id', errorId);

            // Format timestamp
            const timestamp = error.timestamp ?
                new Date(error.timestamp).toLocaleTimeString() :
                new Date().toLocaleTimeString();

            // Format machine name
            const machine = error.machine || 'unknown';

            // Format message
            let message = error.message || error.event_name;
            let level = error.level || 'error';

            // Parse JSON payloads for better detail
            try {
                // First try to parse the payload field
                if (error.payload) {
                    const payload = JSON.parse(error.payload);

                    // Handle activity_log events
                    if (payload.message) {
                        message = payload.message;
                        level = payload.level || level;
                    }
                    // Handle error events with reason/stage
                    else if (payload.reason) {
                        message = payload.reason;
                    } else if (payload.stage) {
                        message = `${payload.stage}${payload.reason ? ': ' + payload.reason : ''}`;
                    }
                }
            } catch (e) {
                // Not JSON, use as-is
            }

            // Set entry class with parsed level
            entry.className = `log-entry ${level}`;

            // Build detailed message with job_id
            let detailParts = [];
            if (error.job_id) {
                detailParts.push(`<strong>${error.job_id}</strong>`);
            }
            if (error.event_name && error.event_name !== message) {
                detailParts.push(error.event_name);
            }
            detailParts.push(message);

            const detailedMessage = detailParts.join(' - ');

            entry.innerHTML = `
                <span class="timestamp">[${timestamp}]</span>
                <span class="machine">${machine}</span>
                <span class="message">${detailedMessage}</span>
            `;

            // Add to top of log
            this.activityLog.insertBefore(entry, this.activityLog.firstChild);
            existingErrors.add(errorId);
        });

        // Keep only last 100 entries total (errors + activity)
        while (this.activityLog.children.length > 100) {
            this.activityLog.removeChild(this.activityLog.lastChild);
        }
    }

    logActivity(level, message) {
        const timestamp = new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = `log-entry ${level}`;
        entry.innerHTML = `
            <span class="timestamp">[${timestamp}]</span>
            <span class="message">${message}</span>
        `;

        // Add to top of log
        this.activityLog.insertBefore(entry, this.activityLog.firstChild);

        // Keep only last 100 entries (consistent with updateActivityLog)
        while (this.activityLog.children.length > 100) {
            this.activityLog.removeChild(this.activityLog.lastChild);
        }
    }

    destroy() {
        this.stopPingInterval();
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
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