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

### 1. Try the Included Examples

The package includes working example configurations:

```bash
# Simple worker example
cd examples/simple_worker
statemachine config/worker.yaml --machine-name worker

# Controller/worker multi-machine example
cd examples/controller_worker
./run.sh
```

See [examples/](examples/) directory for complete working configurations.

### 2. Create Your Own Configuration

```yaml
# my_worker.yaml
name: "My Worker"
initial_state: waiting

transitions:
  - from: waiting
    to: processing
    event: new_job
    actions:
      - type: bash
        params:
          command: "echo Processing job"
          success: job_done
```

### 3. Run Your State Machine

```bash
statemachine my_worker.yaml --machine-name my_worker
```

Or using Python directly:
```python
from statemachine_engine.core.engine import StateMachineEngine

engine = StateMachineEngine(machine_name='my_worker')
await engine.load_config('my_worker.yaml')
await engine.execute_state_machine()
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

### Running the Examples

#### Simple Worker
```bash
cd examples/simple_worker
statemachine config/worker.yaml --machine-name worker

# Or with debug logging:
statemachine config/worker.yaml --machine-name worker --debug
```

#### Controller/Worker (Multi-Machine)
```bash
cd examples/controller_worker

# Option 1: Use the run script
./run.sh

# Option 2: Run in separate terminals
# Terminal 1:
statemachine config/controller.yaml --machine-name controller

# Terminal 2:
statemachine config/worker.yaml --machine-name worker
```

**Available Examples:**
- [Simple Worker](examples/simple_worker/) - Basic job processing with database queue
- [Controller/Worker](examples/controller_worker/) - Multi-machine event coordination

## Documentation

- [Quickstart Guide](docs/quickstart.md) - Get started in 5 minutes
- [CLAUDE.md](CLAUDE.md) - Architecture and development guide

## Development

### Running Tests

```bash
# Install dev dependencies first
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run with detailed output
pytest tests/ -vv

# Run specific test files
pytest tests/actions/test_bash_action_fallback.py -v
pytest tests/communication/test_control_socket.py -v

# Run specific test categories
pytest tests/actions/ -v          # Action tests
pytest tests/communication/ -v     # Communication tests
pytest tests/database/ -v          # Database tests

# Show test summary
pytest tests/ --tb=short

# Run tests with coverage (install pytest-cov first)
pytest tests/ --cov=statemachine_engine --cov-report=html
```

**Current Test Status:** 54 tests total (48 passing, 0 failing, 6 skipped) - 100% pass rate ✅

### Building the Package

```bash
# Build distribution packages
python -m build

# Check the built package
ls dist/
# statemachine_engine-1.0.0-py3-none-any.whl
# statemachine_engine-1.0.0.tar.gz
```

## License

MIT License - see [LICENSE](LICENSE) file

## Repository

https://github.com/sheikkinen/statemachine-engine
