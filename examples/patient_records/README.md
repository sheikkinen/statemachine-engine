# Patient Records Demo

This demo showcases the **Kanban visualization feature** for concurrent FSM instances. It simulates a patient record processing workflow with multiple reports being processed simultaneously.

## Workflow Overview

The patient records FSM implements a 4-state workflow:

```
waiting_for_report → summarizing → fact_checking → ready
                          ↓             ↓
                    (retry loops for validation)
                          ↓             ↓  
                    waiting_for_report ←─────┘
                          ↓
                       failed
```

### States

1. **waiting_for_report** - Initial state, waiting for new report to process
2. **summarizing** - Converting report into paragraph summary
3. **fact_checking** - Validating that summary is based on report content
4. **ready** - Report processed successfully, ready for history generation
5. **failed** - Processing failed, needs manual intervention

### Events

- `new_report` - Start processing a new medical report
- `summary_complete` - Summary generation finished successfully
- `summary_invalid` - Summary doesn't match report, retry needed
- `validation_passed` - Fact check successful, report is ready
- `validation_failed` - Fact check failed, need to re-summarize
- `processing_error` - Technical error occurred
- `retry_report` - Reset failed report for reprocessing
- `process_next` - Move to next report from ready state

## State Groups (Composite Diagrams)

The FSM defines composite state groups for hierarchical visualization:

```yaml
state_groups:
  PROCESSING:
    states: [summarizing, fact_checking]
  COMPLETION:
    states: [ready, failed]
```

This enables the UI to show:
- **Main view**: High-level workflow with composite states
- **Detailed view**: Individual states within each composite
- **Kanban view**: Cards moving between processing stages

## Demo Features

### Realistic Processing Simulation
- **Automatic timeouts**: summarizing (10s), fact_checking (5s)
- **Validation loops**: Reports can fail and retry automatically
- **Random events**: Continuous simulation with realistic timing
- **Rich logging**: Detailed activity logs with emojis and context

### Concurrent Instance Testing
- **10 concurrent machines** processing different reports simultaneously
- **Staggered startup** to simulate real-world load patterns
- **Individual logging** for each machine instance
- **Real-time monitoring** via WebSocket events

### Kanban Visualization
- **Column-based view**: waiting | summarizing | fact_checking | ready | failed
- **Real-time updates**: Cards move between columns as states change
- **Instance details**: Each card shows report ID, title, and current status
- **Keyboard shortcut**: Press 'K' to toggle Kanban view

## Usage

### Quick Start
```bash
# Start the demo with 10 concurrent instances
./run-demo.sh start

# Open browser to http://localhost:3002
# Press 'K' key to open Kanban view

# Watch real-time events in another terminal
./run-demo.sh events

# Add continuous simulation for dynamic demo
./run-demo.sh continuous
```

### Available Commands
```bash
./run-demo.sh start      # Start 10 machines + monitoring
./run-demo.sh continuous # Dynamic event simulation  
./run-demo.sh events     # Real-time event viewer
./run-demo.sh status     # Show machine status
./run-demo.sh cleanup    # Stop all machines
./run-demo.sh help       # Show detailed help
```

### Sample Output
```
🏥 Starting Patient Records Demo with 10 instances...
📡 Starting WebSocket monitoring server...
   └─ PID: 12345, URL: http://localhost:3002

🏥 Starting machine: patient_record_1
   └─ PID: 12346, Log: logs/patient_record_1.log
🏥 Starting machine: patient_record_2
   └─ PID: 12347, Log: logs/patient_record_2.log
...

📨 Sending sample events to create realistic workflow...
   └─ Sending new_report to patient_record_1: Annual Physical Examination
   └─ Sending new_report to patient_record_2: Blood Test Results - Full Panel
...

📊 Demo running! Open http://localhost:3002 and press 'K' for Kanban view
💡 Events will process automatically via timeouts (10s summarizing, 5s fact-checking)
```

## Technical Implementation

### FSM Configuration
- **YAML-based configuration** with state groups for composite visualization
- **Timeout-driven progression** for realistic processing simulation
- **Loop transitions** for validation retry logic
- **Rich context variables** for report tracking

### Multi-Instance Architecture
- **Machine naming**: `patient_record_1`, `patient_record_2`, etc.
- **Individual logging**: Separate log file per instance
- **Process management**: PID tracking for clean shutdown
- **Event distribution**: Targeted events to specific machines

### Monitoring Integration
- **WebSocket events** broadcast state changes in real-time
- **Database persistence** for audit trail and recovery
- **UI integration** with existing diagram manager
- **Kanban enhancement** for concurrent instance visualization

## Use Cases

### Development Testing
- **Concurrent FSM validation** - Ensure multiple instances work correctly
- **WebSocket stress testing** - Verify real-time updates with high event volume
- **UI responsiveness** - Test Kanban view with rapid state changes
- **Resource management** - Monitor memory/CPU usage with many instances

### Demo Scenarios
- **Medical workflow automation** showcase
- **Real-time monitoring** capabilities demonstration  
- **Scalability validation** with concurrent processing
- **User interface innovation** with Kanban visualization

### Educational Examples
- **FSM design patterns** for retry logic and validation loops
- **Composite state modeling** for hierarchical workflows
- **Event-driven architecture** with timeout-based progression
- **Modern UI patterns** for complex state visualization

## Expected Kanban Behavior

When the Kanban feature is implemented:

1. **Press 'K'** in the UI to open Kanban modal
2. **See columns**: waiting_for_report | summarizing | fact_checking | ready | failed  
3. **Watch cards move** automatically as timeouts trigger state changes
4. **Click cards** to see individual FSM diagram details
5. **Real-time updates** as continuous events simulate workflow activity

The demo provides the perfect test bed for validating the Kanban visualization with realistic concurrent FSM instances.