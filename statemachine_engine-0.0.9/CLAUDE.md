# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

TDD. DRY. KISS. YAGNI.

## Background

**State Machine Engine** is a generic event-driven state machine framework with real-time monitoring. It provides the core infrastructure for building workflow automation systems with:

- YAML-based workflow configuration
- Pluggable action system
- Real-time WebSocket monitoring
- Database-backed job queue
- Unix socket communication
- FSM diagram generation

## Architecture

**Core Components:**

1. **State Machine Engine** (`src/statemachine_engine/core/engine.py`)
   - Event-driven state transitions
   - Action execution framework
   - Job queue integration
   - Real-time event emission

2. **Action System** (`src/statemachine_engine/actions/`)
   - BaseAction interface for custom actions
   - 6 built-in actions (bash, log, events, queue checks)
   - Dynamic action loading
   - Action registry pattern

3. **Database Layer** (`src/statemachine_engine/database/`)
   - SQLite-based job storage
   - Machine event tracking
   - Machine state persistence
   - Realtime event queue

4. **Monitoring** (`src/statemachine_engine/monitoring/`)
   - WebSocket server (port 3002)
   - Real-time event broadcasting
   - Database fallback polling

5. **Tools** (`src/statemachine_engine/tools/`)
   - FSM diagram generator
   - YAML configuration validator

## Development Guidelines

### Adding New Built-in Actions

1. Create action file in `src/statemachine_engine/actions/builtin/`
2. Extend `BaseAction` class
3. Implement `async def execute(self, context) -> str`
4. Add tests in `tests/actions/`
5. Update `builtin/__init__.py` exports
6. Update documentation

**Example:**
```python
# src/statemachine_engine/actions/builtin/my_action.py
from ..base import BaseAction

class MyAction(BaseAction):
    async def execute(self, context):
        # Your logic here
        return 'success'
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test category
pytest tests/actions/ -v
pytest tests/communication/ -v
pytest tests/database/ -v
```

### Building & Installing

```bash
# Install in development mode
pip install -e ".[dev]"

# Build package
python -m build

# Install from build
pip install dist/statemachine_engine-1.0.0-py3-none-any.whl
```

## Usage Patterns

### Basic Worker
```yaml
# config/worker.yaml
name: "Simple Worker"
initial_state: waiting

transitions:
  - from: waiting
    to: processing
    event: new_job
    actions:
      - type: check_database_queue

  - from: processing
    to: completed
    event: job_done
    actions:
      - type: bash
        params:
          command: "echo Done"
          success: job_done
```

### Controller + Worker
```yaml
# Worker sends events to controller
actions:
  - type: send_event
    params:
      target: controller
      event_type: task_completed
```

## File Structure

```
statemachine-engine/
├── src/statemachine_engine/
│   ├── core/              # State machine engine
│   ├── actions/           # Action framework + built-ins
│   ├── database/          # Database layer
│   ├── monitoring/        # WebSocket server
│   ├── tools/             # FSM generator
│   └── ui/                # Web UI
├── tests/                 # Test suite
├── examples/              # Example workflows
├── docs/                  # Documentation
└── pyproject.toml         # Package configuration
```

## Communication Architecture

### Unix Socket System

**Control Sockets (Incoming Events):**
- Path: `/tmp/statemachine-control-{machine_name}.sock`
- Purpose: Receive events targeted at specific state machines
- Protocol: JSON messages over Unix datagram sockets
- Usage: `send-event` CLI command sends events here

**Event Socket (Outgoing Broadcasts):**
- Path: `/tmp/statemachine-events.sock`
- Purpose: Broadcast state changes to monitoring systems
- Protocol: JSON messages over Unix datagram socket
- Consumers: WebSocket server relays to browser UI

**WebSocket Server:**
- Port: `ws://localhost:3002/ws/events`
- Purpose: Real-time updates to web UI
- Events: `state_change`, `activity_log`, `job_started`, `job_completed`, `error`

### Event Delivery Mechanism

**How Events Work:**

1. **Sending Events** (via CLI or send_event action):
   ```bash
   python -m statemachine_engine.database.cli send-event \
     --target simple_worker \
     --type new_job \
     --payload '{"data": "value"}'
   ```

2. **Database Logging** (audit trail only):
   - Event written to `machine_events` table
   - Status: `pending` (never changed - table is audit log only)
   - NOT polled by state machines

3. **Socket Delivery** (actual event delivery):
   - Event sent to `/tmp/statemachine-control-{target}.sock`
   - JSON payload: `{type: "new_job", payload: {...}, job_id: 123}`
   - Zero-latency delivery (no polling)

4. **Engine Processing**:
   - Engine receives event via `_check_control_socket()`
   - Stores event data in `context['event_data']`
   - Calls `process_event(event_type)` to trigger transition
   - Executes actions for new state

5. **State Broadcasting**:
   - Engine emits state change to `/tmp/statemachine-events.sock`
   - WebSocket server receives and relays to connected browsers
   - UI updates in real-time

**Event Flow:**
```
CLI/Action → Database (log) → Control Socket → Engine → Event Socket → WebSocket → UI
              (audit only)      (delivery)     (process)  (broadcast)   (relay)    (display)
```

**Important:** The `machine_events` database table is an **audit log only**. Events are NOT read from the database - they are delivered directly through Unix sockets for zero-latency processing.

## Troubleshooting

### Events Not Triggering Transitions

**Symptom:** `send-event` creates database entry but machine doesn't change state

**Common Causes:**

1. **Event not defined in YAML**
   ```yaml
   events:
     - new_job  # Must list all events that can trigger transitions
   ```

2. **No transition for event in current state**
   ```yaml
   transitions:
     - from: waiting
       to: processing
       event: new_job  # Must have transition from current state
   ```

3. **Control socket doesn't exist**
   - Check: `ls -l /tmp/statemachine-control-*.sock`
   - Fix: Ensure state machine is running

4. **Event type mismatch**
   - Event names are case-sensitive
   - Check logs: `tail -f logs/system-startup.log | grep "📥 Received"`

**Debugging:**
```bash
# Check if machine is running
ps aux | grep statemachine

# Watch for incoming events
tail -f logs/system-startup.log | grep -E "Received event|--.*-->"

# Send test event
python -m statemachine_engine.database.cli send-event \
  --target simple_worker --type new_job
```

## Contributing

1. Fork repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request

## License

MIT License - see LICENSE file

---

**Note:** This is a generic state machine engine. For domain-specific implementations, create your own actions in `actions/` directory and reference them in YAML configs.
