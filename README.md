# State Machine Engine

Event-driven state machine framework with real-time monitoring and database-backed job queue.

## Features

- **YAML-Based Configuration**: Define workflows declaratively
- **Pluggable Actions**: Extensible action system with built-in actions
- **Real-Time Monitoring**: WebSocket server for live state visualization
- **Database-Backed Queue**: SQLite-based persistent job queue
- **Unix Socket Communication**: Low-latency inter-machine events
- **Multi-Machine Coordination**: Event-driven machine-to-machine communication

## Installation

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/sheikkinen/statemachine-engine.git
cd statemachine-engine

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Option 1: Install with pip (uses pyproject.toml)
pip install -e ".[dev]"

# Option 2: Install with requirements files
pip install -r requirements-dev.txt
```

### From PyPI (Coming Soon)

```bash
pip install statemachine-engine
```

### Dependencies

The package requires Python 3.9+ and automatically installs:
- PyYAML (YAML configuration parsing)
- FastAPI (WebSocket server)
- Uvicorn (ASGI server)
- websockets (WebSocket protocol)

Development dependencies (optional):
- pytest (testing framework)
- pytest-asyncio (async test support)

## Quick Start

### 1. Create a Configuration File

```yaml
# worker.yaml
name: "Simple Worker"
initial_state: waiting

states:
  - waiting
  - processing
  - completed

events:
  - new_job
  - job_done

transitions:
  - from: waiting
    to: processing
    event: new_job
    actions:
      - type: check_database_queue
        params:
          job_type: task

  - from: processing
    to: completed
    event: job_done
    actions:
      - type: bash
        params:
          command: "echo Processed {job_id}"
          success: job_done
```

### 2. Run the State Machine

```bash
statemachine worker.yaml --machine-name worker
```

Or using Python:
```python
from statemachine_engine import StateMachineEngine

engine = StateMachineEngine('worker.yaml', machine_name='worker')
engine.run()
```

## Built-In Actions

- **bash**: Execute shell commands
- **log**: Activity logging
- **check_database_queue**: Check job queue for pending jobs
- **check_machine_state**: Monitor machine states
- **clear_events**: Clean up processed events
- **send_event**: Send events to other machines

## Custom Actions

Create custom actions by extending `BaseAction`:

```python
from statemachine_engine.actions import BaseAction

class MyAction(BaseAction):
    async def execute(self, context):
        # Your logic here
        return 'success'  # Return event name
```

## Multi-Machine Setup

State machines can communicate via events:

```yaml
# worker.yaml
transitions:
  - from: processing
    to: notifying
    event: job_done
    actions:
      - type: send_event
        params:
          target: controller
          event_type: task_completed
```

## Real-Time Monitoring

Start the WebSocket server for live monitoring:

```bash
python -m statemachine_engine.monitoring.websocket_server
```

Access the web UI at `http://localhost:3001`

## Examples

See the [examples/](examples/) directory for:
- [Simple Worker](examples/simple_worker/) - Basic job processing
- [Controller/Worker](examples/controller_worker/) - Multi-machine coordination

## Documentation

- [Quickstart Guide](docs/quickstart.md) - Get started in 5 minutes
- [CLAUDE.md](CLAUDE.md) - Architecture and development guide

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test category
pytest tests/actions/ -v
pytest tests/communication/ -v
```

### Building the Package

```bash
python -m build
```

## License

MIT License - see [LICENSE](LICENSE) file

## Repository

https://github.com/sheikkinen/statemachine-engine
