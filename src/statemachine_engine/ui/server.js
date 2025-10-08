const express = require('express');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(express.static('public'));
app.use(express.json());

// Path to the project root - use environment variable if set, otherwise assume UI is in src/statemachine_engine/ui/
const PROJECT_ROOT = process.env.PROJECT_ROOT || path.join(__dirname, '../../..');

// Get machine states using existing CLI
function getMachineStates() {
    return new Promise((resolve, reject) => {
        const child = spawn('python', ['-m', 'statemachine_engine.database.cli', 'machine-state', '--format', 'json'], {
            cwd: PROJECT_ROOT
        });
        
        let output = '';
        let error = '';
        
        child.stdout.on('data', (data) => {
            output += data.toString();
        });
        
        child.stderr.on('data', (data) => {
            error += data.toString();
        });
        
        child.on('close', (code) => {
            if (code === 0) {
                try {
                    const machines = JSON.parse(output);
                    resolve(machines);
                } catch (e) {
                    reject(new Error(`Failed to parse JSON: ${e.message}`));
                }
            } else {
                reject(new Error(`CLI command failed: ${error}`));
            }
        });
    });
}

// Check if machine process is running
function checkProcessRunning(machineName) {
    return new Promise((resolve) => {
        const child = spawn('ps', ['aux'], {});
        let output = '';

        child.stdout.on('data', (data) => {
            output += data.toString();
        });

        child.on('close', () => {
            const isRunning = output.includes(`statemachine`) &&
                             output.includes(machineName);
            resolve(isRunning);
        });
    });
}

// Get recent errors for activity log
function getRecentErrors(limit = 10) {
    return new Promise((resolve, reject) => {
        const child = spawn('python', [
            '-m', 'statemachine_engine.database.cli',
            'list-errors',
            '--format', 'json',
            '--limit', limit.toString()
        ], {
            cwd: PROJECT_ROOT
        });

        let output = '';
        let error = '';

        child.stdout.on('data', (data) => {
            output += data.toString();
        });

        child.stderr.on('data', (data) => {
            error += data.toString();
        });

        child.on('close', (code) => {
            if (code === 0) {
                try {
                    const errors = JSON.parse(output);
                    resolve(errors);
                } catch (e) {
                    reject(new Error(`Failed to parse errors: ${e.message}`));
                }
            } else {
                reject(new Error(`CLI command failed: ${error}`));
            }
        });
    });
}

// API Routes

// Get FSM diagram for a specific machine (OLD FORMAT - for backward compatibility)
app.get('/api/diagram/:machine_name', (req, res) => {
    const { machine_name } = req.params;
    // Check new location first, fall back to old location
    let fsmDocPath = path.join(PROJECT_ROOT, 'docs', 'fsm-diagrams', machine_name, `${machine_name}_fsm.md`);
    if (!fs.existsSync(fsmDocPath)) {
        fsmDocPath = path.join(PROJECT_ROOT, 'docs', `${machine_name}_fsm.md`);
    }

    try {
        // Check if FSM doc exists
        if (!fs.existsSync(fsmDocPath)) {
            return res.status(404).json({ error: `Diagram not found for machine: ${machine_name}` });
        }

        // Read the markdown file
        const content = fs.readFileSync(fsmDocPath, 'utf-8');

        // Extract the main Mermaid diagram (first code block)
        const match = content.match(/```mermaid\n([\s\S]*?)\n```/);

        if (match) {
            res.json({
                machine_name,
                diagram: match[1]
            });
        } else {
            res.status(404).json({ error: 'No Mermaid diagram found in document' });
        }
    } catch (error) {
        console.error(`Error reading diagram for ${machine_name}:`, error);
        res.status(500).json({ error: error.message });
    }
});

// Get metadata for a machine (all diagrams info)
// IMPORTANT: This route must come BEFORE the :diagram_name route to avoid matching "metadata" as a diagram name
app.get('/api/diagram/:machine_name/metadata', (req, res) => {
    const { machine_name } = req.params;
    
    try {
        const metadataPath = path.join(PROJECT_ROOT, 'docs', 'fsm-diagrams', machine_name, 'metadata.json');
        
        if (!fs.existsSync(metadataPath)) {
            return res.status(404).json({ 
                error: `Machine not found: ${machine_name}` 
            });
        }
        
        const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf-8'));
        res.json(metadata);
    } catch (error) {
        console.error(`Error reading metadata for ${machine_name}:`, error);
        res.status(500).json({ error: error.message });
    }
});

// Get FSM diagram with hierarchical navigation (NEW FORMAT)
app.get('/api/diagram/:machine_name/:diagram_name', (req, res) => {
    const { machine_name, diagram_name } = req.params;
    
    try {
        // Load metadata
        const metadataPath = path.join(PROJECT_ROOT, 'docs', 'fsm-diagrams', machine_name, 'metadata.json');
        
        if (!fs.existsSync(metadataPath)) {
            return res.status(404).json({ 
                error: `Machine not found: ${machine_name}`,
                hint: 'Machine may not have composite states. Use /api/diagram/:machine_name instead.'
            });
        }
        
        const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf-8'));
        
        // Validate diagram exists
        if (!metadata.diagrams[diagram_name]) {
            return res.status(404).json({ 
                error: `Diagram not found: ${diagram_name}`,
                available_diagrams: Object.keys(metadata.diagrams),
                machine_name: machine_name
            });
        }
        
        // Read Mermaid file directly (no parsing!)
        const diagramInfo = metadata.diagrams[diagram_name];
        const diagramPath = path.join(PROJECT_ROOT, 'docs', 'fsm-diagrams', machine_name, diagramInfo.file);
        
        if (!fs.existsSync(diagramPath)) {
            return res.status(500).json({ 
                error: `Diagram file not found: ${diagramInfo.file}` 
            });
        }
        
        const mermaidCode = fs.readFileSync(diagramPath, 'utf-8');
        
        // Return diagram + metadata
        res.json({
            machine_name,
            diagram_name,
            mermaid_code: mermaidCode,
            metadata: {
                title: diagramInfo.title || diagram_name,
                description: diagramInfo.description || '',
                composites: diagramInfo.composites || [],
                states: diagramInfo.states || [],
                parent: diagramInfo.parent || null,
                entry_states: diagramInfo.entry_states || [],
                exit_states: diagramInfo.exit_states || []
            }
        });
    } catch (error) {
        console.error(`Error reading diagram ${machine_name}/${diagram_name}:`, error);
        res.status(500).json({ error: error.message });
    }
});

// Get all machine states
app.get('/api/machines', async (req, res) => {
    try {
        const machines = await getMachineStates();

        // Add process status to each machine
        const machinesWithStatus = await Promise.all(
            machines.map(async (machine) => {
                const isRunning = await checkProcessRunning(machine.machine_name);
                return {
                    ...machine,
                    running: isRunning
                };
            })
        );

        res.json(machinesWithStatus);
    } catch (error) {
        console.error('Error getting machine states:', error);
        res.status(500).json({ error: error.message });
    }
});

// Get error events for activity log
app.get('/api/errors', async (req, res) => {
    const limit = req.query.limit || 50;

    try {
        const child = spawn('python', [
            '-m', 'statemachine_engine.database.cli',
            'list-errors',
            '--format', 'json',
            '--limit', limit.toString()
        ], {
            cwd: PROJECT_ROOT
        });

        let output = '';
        let error = '';

        child.stdout.on('data', (data) => {
            output += data.toString();
        });

        child.stderr.on('data', (data) => {
            error += data.toString();
        });

        child.on('close', (code) => {
            if (code === 0) {
                try {
                    const errors = JSON.parse(output);
                    res.json(errors);
                } catch (e) {
                    res.status(500).json({ error: `Failed to parse errors: ${e.message}` });
                }
            } else {
                res.status(500).json({ error: `Failed to fetch errors: ${error}` });
            }
        });
    } catch (error) {
        console.error('Error fetching errors:', error);
        res.status(500).json({ error: error.message });
    }
});

// Start a machine
app.post('/api/machine/:name/start', async (req, res) => {
    const { name } = req.params;
    const { configPath } = req.body;

    try {
        if (!configPath) {
            return res.status(400).json({
                error: 'Config path required',
                message: 'Please provide configPath in request body'
            });
        }

        // Start the machine process in background
        const child = spawn('statemachine', [
            configPath,
            '--machine-name', name,
            '--debug'
        ], {
            cwd: PROJECT_ROOT,
            detached: true,
            stdio: 'ignore'
        });

        child.unref(); // Allow parent to exit

        res.json({
            success: true,
            message: `Started machine: ${name}`,
            pid: child.pid
        });
    } catch (error) {
        console.error(`Error starting machine ${name}:`, error);
        res.status(500).json({ error: error.message });
    }
});

// Stop a machine
app.post('/api/machine/:name/stop', async (req, res) => {
    const { name } = req.params;
    
    try {
        // Send stop event using existing CLI
        const child = spawn('python', [
            '-m', 'statemachine_engine.database.cli',
            'send-event',
            '--target', name,
            '--type', 'stop'
        ], {
            cwd: PROJECT_ROOT
        });
        
        let output = '';
        let error = '';
        
        child.stdout.on('data', (data) => {
            output += data.toString();
        });
        
        child.stderr.on('data', (data) => {
            error += data.toString();
        });
        
        child.on('close', (code) => {
            if (code === 0) {
                res.json({ 
                    success: true, 
                    message: `Stop event sent to machine: ${name}` 
                });
            } else {
                res.status(500).json({ 
                    error: `Failed to stop machine: ${error}` 
                });
            }
        });
    } catch (error) {
        console.error(`Error stopping machine ${name}:`, error);
        res.status(500).json({ error: error.message });
    }
});

// Legacy SSE endpoint - DEPRECATED
// The web UI now uses WebSocket connection to ws://localhost:3002/ws/events
// This endpoint is kept for backward compatibility but should not be used
app.get('/api/events', (req, res) => {
    console.warn('⚠️  DEPRECATED: Client requested /api/events (SSE). Please use WebSocket at ws://localhost:3002/ws/events');
    
    res.writeHead(410, {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    });
    
    res.end(JSON.stringify({
        error: 'SSE endpoint deprecated',
        message: 'This endpoint has been replaced with WebSocket for real-time communication.',
        migration: {
            old: 'EventSource(\'/api/events\')',
            new: 'WebSocket(\'ws://localhost:3002/ws/events\')',
            documentation: 'See docs/plan-websocket-migration.md for details'
        }
    }));
});

// Start server
app.listen(PORT, () => {
    console.log(`State Machine UI running at http://localhost:${PORT}`);
    console.log(`Project root: ${PROJECT_ROOT}`);
});