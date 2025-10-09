# Event Monitor Tool

## Overview

CLI tool that monitors state machine events in real-time by connecting to WebSocket server.

**Command**: `statemachine-events`

**Features**:
- Display all state changes from all machines
- Filter by machine name
- Output formats: human, json, compact
- Time-limited monitoring
- Remote monitoring via WebSocket

**Event Flow**:
```
State Machine → Unix Socket → WebSocket Server → Event Monitor → Terminal
     (engine)      (DGRAM)        (port 3002)      (WS client)
```

## Implementation

**File**: `src/statemachine_engine/tools/event_monitor.py`  
**Entry Point**: Added to pyproject.toml as `statemachine-events`

## Core Design

**Key Classes**:
- `EventMonitor`: Connects to socket, formats events, handles output
- Formats: `human` (default), `json`, `compact`
- Filters: By machine name, duration limit

**Output Examples**:
```
# Human format
[06:32:27] simple_worker: initializing → waiting (initialized)
[06:32:30] simple_worker: waiting → processing (new_job)

# JSON format
{"machine_name":"simple_worker","event_type":"state_change","to_state":"waiting"}

# Compact format
simple_worker → waiting
```

## Usage

```bash
statemachine-events                              # All events
statemachine-events --machine simple_worker      # Filter machine
statemachine-events --format json > events.log   # JSON output
statemachine-events --duration 60                # Time limit
```

## Implementation Checklist

- [x] Plan and design
- [x] Create `src/statemachine_engine/tools/event_monitor.py`
- [x] Add `statemachine-events` to pyproject.toml
- [x] Update CLAUDE.md
- [x] Update README.md
- [x] Test with examples (see `monitor-test/` directory)
- [x] Create test scripts in `monitor-test/`

## Testing

See `monitor-test/` directory for complete test suite with proper log redirection.

```bash
# Automated full test
cd monitor-test
./test-full.sh

# Interactive testing
./start-websocket.sh  # Terminal 1
./start-worker.sh     # Terminal 2
./run-monitor.sh      # Terminal 3
./send-event.sh       # Terminal 4 (send events)

# Quick test
./quick-test.sh       # Auto-starts everything, then monitors

# Clean up
./cleanup.sh
```

**Test Results** (from `./test-full.sh`):
```
[18:59:40.384] 📝 simple_worker: 📥 Received new_job
[18:59:40.384] 🔄 simple_worker: waiting --new_job--> processing
[18:59:42.404] 🔄 simple_worker: processing --job_done--> completed
[18:59:42.464] 🔄 simple_worker: completed --continue_work--> waiting
```

✅ **All tests passing** - monitor successfully captures state transitions and events.

## Why This Approach

**Non-invasive**: Observes broadcasts without affecting event delivery  
**Simple**: WebSocket client connection, minimal code  
**Complete**: Sees all events from all machines  
**Reusable**: General debugging tool, not test-specific  
**Remote-capable**: Can monitor state machines on remote servers via WebSocket  
**Browser-compatible**: Same infrastructure as web UI
