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

**Unix Socket System:**
- Control sockets: `/tmp/statemachine-control-{machine_name}.sock`
- Event socket: `/tmp/statemachine-events.sock`
- WebSocket: `ws://localhost:3002/ws`

**Event Flow:**
```
Job Creation → Control Socket → State Machine → Event Socket → WebSocket → UI
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
