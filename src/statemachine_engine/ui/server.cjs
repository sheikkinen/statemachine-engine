const express = require('express');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3001;
const WEBSOCKET_PORT = process.env.WEBSOCKET_PORT || 3002;

console.log(`🌐 UI Port: ${PORT}, 🔌 WebSocket Port: ${WEBSOCKET_PORT}`);

// Middleware
app.use(express.static('public'));
app.use(express.json());

// Path to the project root - use environment variable if set, otherwise assume UI is in src/statemachine_engine/ui/
const PROJECT_ROOT = process.env.PROJECT_ROOT || path.join(__dirname, '../../..');

// Resolve diagram directory for a machine name.
// Dynamic machine names (e.g. "telephony-CA123") may not have their own diagram
// directory.  Fall back to the longest prefix match among existing directories
// so that "telephony-CA123" resolves to the "telephony" diagram.
function resolveDiagramDir(machineName) {
    const diagramsRoot = path.join(PROJECT_ROOT, 'docs', 'fsm-diagrams');
    const exact = path.join(diagramsRoot, machineName);
    if (fs.existsSync(exact)) return machineName;

    // Prefix fallback: find the longest directory name that is a prefix of machineName
    // and actually contains a diagram file.
    try {
        const dirs = fs.readdirSync(diagramsRoot, { withFileTypes: true })
            .filter(d => d.isDirectory())
            .map(d => d.name)
            .filter(d => machineName.startsWith(d + '-') || machineName.startsWith(d))
            .filter(d => {
                // Only match directories that contain at least one diagram file
                const fsmDoc = path.join(diagramsRoot, d, `${d}_fsm.md`);
                const metadata = path.join(diagramsRoot, d, 'metadata.json');
                return fs.existsSync(fsmDoc) || fs.existsSync(metadata);
            })
            .sort((a, b) => b.length - a.length);
        if (dirs.length > 0) return dirs[0];
    } catch (_) { /* diagramsRoot may not exist */ }
    return null;
}

// API Configuration endpoint
app.get('/api/config', (req, res) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.json({
        websocket_url: `ws://localhost:${WEBSOCKET_PORT}/ws/events`,
        websocket_port: parseInt(WEBSOCKET_PORT),
        ui_port: parseInt(PORT)
    });
});

// API Routes

// Get FSM diagram for a specific machine (OLD FORMAT - for backward compatibility)
app.get('/api/diagram/:machine_name', (req, res) => {
    const { machine_name } = req.params;
    const resolvedDir = resolveDiagramDir(machine_name);
    // Check new location first, fall back to old location
    let fsmDocPath = resolvedDir
        ? path.join(PROJECT_ROOT, 'docs', 'fsm-diagrams', resolvedDir, `${resolvedDir}_fsm.md`)
        : null;
    if (!fsmDocPath || !fs.existsSync(fsmDocPath)) {
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
    const resolvedDir = resolveDiagramDir(machine_name) || machine_name;

    try {
        const metadataPath = path.join(PROJECT_ROOT, 'docs', 'fsm-diagrams', resolvedDir, 'metadata.json');

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
    const resolvedDir = resolveDiagramDir(machine_name) || machine_name;

    try {
        // Load metadata
        const metadataPath = path.join(PROJECT_ROOT, 'docs', 'fsm-diagrams', resolvedDir, 'metadata.json');

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
        const diagramPath = path.join(PROJECT_ROOT, 'docs', 'fsm-diagrams', resolvedDir, diagramInfo.file);

        if (!fs.existsSync(diagramPath)) {
            return res.status(500).json({
                error: `Diagram file not found: ${diagramInfo.file}`
            });
        }

        const mermaidCode = fs.readFileSync(diagramPath, 'utf-8');

        // Return diagram + COMPLETE metadata (needed for state highlighting map)
        res.json({
            machine_name,
            diagram_name,
            mermaid_code: mermaidCode,
            metadata: metadata  // Return the full metadata object with all diagrams
        });
    } catch (error) {
        console.error(`Error reading diagram ${machine_name}/${diagram_name}:`, error);
        res.status(500).json({ error: error.message });
    }
});

// Legacy SSE endpoint - DEPRECATED
// The web UI now uses WebSocket connection via /api/config
// This endpoint is kept for backward compatibility but should not be used
app.get('/api/events', (req, res) => {
    console.warn('⚠️  DEPRECATED: Client requested /api/events (SSE). Please use WebSocket from /api/config');

    res.writeHead(410, {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    });

    res.end(JSON.stringify({
        error: 'SSE endpoint deprecated',
        message: 'This endpoint has been replaced with WebSocket for real-time communication.',
        migration: {
            old: 'EventSource(\'/api/events\')',
            new: 'WebSocket configured via /api/config',
            documentation: 'See docs/plan-websocket-migration.md for details'
        }
    }));
});

// Start server
app.listen(PORT, () => {
    console.log(`State Machine UI running at http://localhost:${PORT}`);
    console.log(`Project root: ${PROJECT_ROOT}`);
});
