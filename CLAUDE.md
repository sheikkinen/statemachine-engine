# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

TDD. DRY. KISS. YAGNI.

## Background

**State Machine Engine** v0.1.0 - Generic event-driven FSM framework for workflow automation with real-time monitoring and zero-latency Unix socket communication.

**Key Capabilities:**
- YAML-based workflow configuration with variable interpolation (`{var}`, `{nested.path}`)
- 6 built-in actions + pluggable custom action system
- Real-time WebSocket monitoring (port 3002)
- SQLite job queue with machine-agnostic polling
- Unix socket IPC for sub-millisecond event delivery
- FSM diagram generation and validation tools

## Architecture

**Core Components:**

1. **Engine** (`core/engine.py` - 666 lines)
   - Event-driven FSM with async/await
   - Engine-level variable interpolation for all actions
   - Control socket listener for incoming events
   - Event socket broadcaster for state changes
   - Health monitoring and graceful shutdown

2. **Actions** (`actions/`)
   - `BaseAction` interface: `async execute(context) -> str`
   - 6 built-in: bash, log, send_event, check_database_queue, check_machine_state, clear_events
   - ActionLoader: dynamic discovery of custom actions
   - All actions benefit from engine-level interpolation

3. **Database** (`database/`)
   - 4 models: Job, MachineEvent, MachineState, RealtimeEvent
   - CLI with 20+ commands: send-event, get-next-job, list-jobs, history
   - Machine-agnostic job claiming for centralized controllers
   - Audit trail (events table is read-only after write)

4. **Monitoring** (`monitoring/websocket_server.py`)
   - FastAPI WebSocket server on port 3002
   - Listens to `/tmp/statemachine-events.sock`
   - Database fallback polling (500ms) if socket quiet
   - CORS-enabled for local development

5. **Tools** (`tools/`)
   - `statemachine-diagrams`: Graphviz FSM visualization
   - `statemachine-validate`: YAML syntax/semantic validation
   - `statemachine-events`: Real-time event monitor CLI

## Development Guidelines

### Adding Built-in Actions

1. Create `src/statemachine_engine/actions/builtin/my_action.py`
2. Extend `BaseAction`, implement `async def execute(self, context) -> str`
3. Modify context for downstream actions: `context['result'] = value`
4. Export in `builtin/__init__.py`
5. Add tests in `tests/actions/test_my_action.py`

**Example:**
```python
from ..base import BaseAction

class MyAction(BaseAction):
    async def execute(self, context):
        # Access params (already interpolated by engine)
        value = self.params.get('input')
        # Modify context for next actions
        context['output'] = f"Processed: {value}"
        return 'success'  # Return event to trigger (or None)
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

### Basic Worker with Variable Interpolation
```yaml
name: "Worker"
initial_state: waiting

transitions:
  - from: waiting
    to: processing
    event: new_job
    actions:
      - type: check_database_queue  # Sets context['job_id'], context['command']
      - type: bash
        params:
          command: "{command}"        # Engine interpolates {command} from context
          success: job_done
          failure: job_failed

  - from: processing
    to: completed
    event: job_done
    actions:
      - type: log
        message: "Completed job {job_id}"  # Interpolation works everywhere
```

### Multi-Machine Communication
```yaml
# Worker sends events to controller
- type: send_event
  params:
    target: controller
    event_type: task_completed
    payload:
      job_id: "{job_id}"        # Nested interpolation supported
      result: "{nested.path}"   # Dot notation for nested context
```

## File Structure

```
statemachine-engine/
├── src/statemachine_engine/
│   ├── core/              # engine.py (666 lines), action_loader.py (278), health_monitor.py (236)
│   ├── actions/           # base.py + builtin/{bash,log,send_event,check_*,clear_events}
│   ├── database/          # models/ + cli.py (64KB - comprehensive CLI)
│   ├── monitoring/        # websocket_server.py (FastAPI + Unix socket listener)
│   ├── tools/             # diagrams.py, validate.py, event_monitor.py, cli.py
│   └── ui/                # Web interface (separate package)
├── tests/                 # Comprehensive test suite (actions/, core/, database/, communication/)
├── examples/              # simple_worker/, controller_worker/, custom_actions/
└── pyproject.toml         # v0.1.0, Python 3.9+, 7 CLI entry points
```

## Communication Architecture

### Socket-Based Zero-Latency IPC

**Control Sockets** (incoming): `/tmp/statemachine-control-{machine_name}.sock`
- Per-machine Unix datagram sockets for targeted event delivery
- Polled every 50ms by engine's `_check_control_socket()`
- JSON payload: `{type: "event_name", payload: {...}, job_id: 123}`

**Event Socket** (outgoing): `/tmp/statemachine-events.sock`
- Single shared broadcast socket for all state changes
- Engine emits: state transitions, errors, activity logs
- Consumed by WebSocket server for UI relay

**WebSocket Server**: `ws://localhost:3002/ws/events`
- Browser-facing real-time event stream
- Receives from Unix socket + database polling fallback
- Event types: `state_change`, `activity_log`, `job_started`, `job_completed`, `error`

### Event Flow

```
send-event CLI → DB audit log → Control Socket → Engine poll (50ms) → Transition → Event Socket → WebSocket → UI
                 (never read)     (/tmp/...)      (_check_control)    (actions)    (broadcast)    (relay)
```

**Key Points:**
- Database `machine_events` table is write-only audit trail (status always 'pending')
- Actual delivery via Unix sockets (sub-millisecond latency)
- Engine polls control socket every 50ms during event loop
- Variable interpolation happens engine-level before action execution
- Context persists across transitions: `context['event_data']`, `context['job_id']`, custom fields

## Troubleshooting

**Events not triggering?**
1. Event not in YAML `events:` list (case-sensitive)
2. No transition from current state (check `from:` matches current state)
3. Control socket missing: `ls -l /tmp/statemachine-control-*.sock`
4. Machine not running: `ps aux | grep statemachine`

**Debugging:**
```bash
# Watch real-time events
statemachine-events

# Check socket delivery
tail -f logs/*.log | grep -E "📥 Received|--.*-->"

# Verify YAML syntax
statemachine-validate config/worker.yaml
```

## Project Principles

- **TDD**: Test-first development (15 tests for v0.1.0 interpolation feature)
- **DRY**: Variable interpolation at engine-level (not per-action)
- **KISS**: Actions return events, engine handles transitions
- **YAGNI**: Build minimal features, extend via custom actions

## Version History

- **v0.1.0** (2025-10-12): Engine-level variable interpolation, machine-agnostic job queue
- Initial release: YAML FSM, 6 built-in actions, Unix socket IPC, WebSocket monitoring

---

**Note:** Generic FSM framework - domain logic goes in custom actions, not core engine.
