# Philosopher's Reflection: FSM UI Architecture

*Analysis date: 2026-03-14*

## Overview

The FSM UI is a **production-quality real-time monitoring system** for state machine workflows. It provides two synchronized views of machine execution and uses WebSocket streaming for sub-second state updates.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Browser (port 3001)                                             │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  app-modular.js (Orchestrator)                              │ │
│  │  ├─ Tab Management (auto-consolidate templated machines)    │ │
│  │  ├─ View Router (Diagram vs Kanban based on metadata)       │ │
│  │  └─ Event Handler Registration                              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌───────────────┬───────────┴───────────┬───────────────────┐  │
│  │ DiagramManager│ KanbanView            │ WebSocketManager  │  │
│  │ - Load diagrams│ - States as columns  │ - Auto-reconnect  │  │
│  │ - Breadcrumb  │ - Machines as cards   │ - Ping/pong       │  │
│  │ - Composites  │ - State groups        │ - Event routing   │  │
│  └───────┬───────┴───────────────────────┴─────────┬─────────┘  │
│          │                                         │            │
│  ┌───────┴───────┐  ┌─────────────────────┐       │            │
│  │MermaidRenderer│  │EventHighlighter     │       │            │
│  │- SVG render   │  │- Fast path (1ms)    │       │            │
│  │- Enrich attrs │  │- Full render (150ms)│       │            │
│  │- Highlight map│  │- Transition anim    │       │            │
│  └───────────────┘  └─────────────────────┘       │            │
└───────────────────────────────────────────────────┼────────────┘
                                                    │
                    WebSocket ws://localhost:3002   │
                                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│  WebSocket Server (port 3002)                                    │
│  - Receives from Unix socket /tmp/statemachine-events.sock       │
│  - Broadcasts to all connected browsers                          │
│  - Database fallback polling (500ms)                             │
└──────────────────────────────────────────────────────────────────┘
                                                    ▲
                    Unix Socket (DGRAM)             │
                                                    │
┌──────────────────────────────────────────────────────────────────┐
│  FSM Engine(s)                                                   │
│  - Emit state_change, machine_started, machine_stopped events    │
│  - Each machine has control socket for receiving commands        │
└──────────────────────────────────────────────────────────────────┘
```

## Codebase Size

| Component | Lines | Purpose |
|-----------|-------|---------|
| app-modular.js | 482 | Main orchestrator, view routing, tab management |
| DiagramManager.js | 297 | Diagram loading, breadcrumb navigation, state persistence |
| MermaidRenderer.js | 266 | Mermaid → SVG rendering, data attribute enrichment |
| EventHighlighter.js | 265 | State highlighting, transition animations |
| KanbanView.js | 250 | Kanban board for templated machines |
| MachineStateManager.js | 219 | Track all machine states |
| WebSocketManager.js | 148 | WebSocket connection management |
| StateGroupManager.js | 130 | Parse YAML state groups |
| style.css | 737 | Dark theme, state highlighting styles |
| index.html | 80 | Entry point, Mermaid CDN import |
| server.cjs | ~200 | Express API server |
| **Total** | **~2,929** | |

## Two View Modes

### 1. Diagram View (Unique Machines)

For machines with distinct configurations (e.g., `controller`, `descriptor`):

- Interactive Mermaid `stateDiagram-v2` rendering
- Click on composite states to drill down (breadcrumb navigation)
- Current state highlighted in real-time
- State persistence across page refreshes (localStorage)

### 2. Kanban View (Templated Machines)

For multiple instances of the same configuration (e.g., `worker_001`, `worker_002`):

- States rendered as columns (left → right)
- Machines rendered as cards within state columns
- Cards move between columns on state changes
- Supports grouped states (vertical stacking within group)

### View Routing

The app auto-detects which view to show based on `metadata.template` flag:

```javascript
// In app-modular.js
isKanbanMachine(config_type) {
    const metadata = this.diagramManager.configMetadata.get(config_type);
    return metadata?.template === true;
}
```

## Fast Path Optimization

The Mermaid renderer builds a **pre-computed state highlight map** during initial render. On subsequent state changes:

- **Fast Path (~1ms)**: Update CSS class on pre-identified DOM element
- **Full Render (~150ms)**: Re-render entire diagram when fast path unavailable

```javascript
// In MermaidRenderer.js
buildStateHighlightMap(metadata) {
    // Pre-compute: state → {type, target, class}
    // Enables O(1) DOM updates instead of O(n) re-render
}
```

## Composite State Support

YAML configurations use comments to define state groups:

```yaml
states:
  # === INITIALIZATION ===
  - initializing
  - loading_config
  # === PROCESSING ===
  - processing
  - validating
```

The UI parses these and renders:
1. **Main Overview**: Composite boxes with entry/exit transitions
2. **Composite Detail**: Click to drill down, shows internal states
3. **Breadcrumb**: Navigate back to parent diagram

## Auto-Consolidating Tabs

Multiple instances of templated machines consolidate into one tab:

```
Machines: face_processor_001, face_processor_002, face_processor_003

Tab Display: Face Processor (3)
```

Clicking the tab shows Kanban view with all instances as cards.

## Event Flow

1. FSM Engine emits event to Unix socket
2. WebSocket server receives, broadcasts to all browsers
3. Browser `WebSocketManager` routes to appropriate handler
4. Handler updates `MachineStateManager`
5. If affected machine is visible:
   - Diagram View: `EventHighlighter.highlightState()`
   - Kanban View: `KanbanView.moveCard()`

## Key Design Decisions

1. **Mermaid v11 from CDN**: Avoids bundling, always latest renderer
2. **Modular ES6 architecture**: Each concern in its own module
3. **Server-Sent State**: UI is purely reactive, no polling
4. **LocalStorage persistence**: Survives page refresh
5. **CSS-only animations**: No JS animation frames

## Relationship to YAMLGraph

This UI is **domain-specific** to the FSM engine — it understands:
- YAML state machine configurations
- Composite state conventions
- Unix socket event format

It's not a generic "Mermaid viewer." However, the architecture patterns could inform a future YAMLGraph monitoring UI:

| FSM Concept | YAMLGraph Equivalent |
|-------------|---------------------|
| State | Node |
| Transition | Edge |
| Composite | Subgraph |
| state_change event | node_completed event |
| Current state highlight | Current node highlight |

## Seed

Could YAMLGraph benefit from a similar real-time monitoring UI? A "Graph Monitor" with:
- Live node highlighting during execution
- Variable/state inspection panel
- Streaming token output for LLM nodes
- Checkpoint/resume visualization

The streaming architecture already exists (WebSocket + event emission). The UI is the missing piece.
