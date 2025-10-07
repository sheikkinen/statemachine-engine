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

### WebSocket Server

Start the WebSocket monitoring server:

```bash
# Direct Python
python -m statemachine_engine.monitoring.websocket_server

```

The server provides:
- Real-time event streaming on `ws://localhost:3002/ws`
- Health check endpoint at `http://localhost:3002/health`
- State machine status monitoring

### Web UI

The package includes a web UI for visualizing state machines (located in `src/statemachine_engine/ui/`):

```bash
cd src/statemachine_engine/ui
npm install  # First time only
npm start    # Starts on http://localhost:3001
```

Features:
- Real-time state visualization with Mermaid diagrams
- Live machine status updates
- Event history and logs

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

## Helper Scripts

The `scripts/` directory contains useful utilities:

### Validate Configurations

```bash
# Validate a single config
./scripts/validate-state-machines.py config/worker.yaml

# Validate all configs
./scripts/validate-state-machines.py examples/**/*.yaml

# Strict mode (exit 1 on warnings)
./scripts/validate-state-machines.py --strict config/*.yaml
```

The validator checks:
- Event coverage (all events have transitions)
- Action emissions (success/error events exist)
- Orphaned/unreachable states
- Missing event declarations
- Self-loop patterns

### Start Worker

```bash
# Start with defaults
./scripts/start-worker.sh

# Specify config and machine name
./scripts/start-worker.sh examples/simple_worker/config/worker.yaml my_worker
```

### Integrated System Startup

```bash
./scripts/start-system.sh
# Comprehensive startup that:
# - Validates all YAML configurations
# - Generates FSM documentation diagrams
# - Starts WebSocket monitoring server
# - Launches state machines
# - Starts Web UI (if Node.js available)
# - Handles graceful shutdown (Ctrl+C)
```

This script provides a complete system startup with:
- Virtual environment activation and validation
- Pre-flight configuration validation
- FSM diagram generation from YAML configs
- WebSocket server with health check polling
- State machine launching
- Web UI startup (optional, requires Node.js)
- Cleanup trap for graceful shutdown

**Usage:**
```bash
# Start the complete system
./scripts/start-system.sh

# View logs while running
tail -f logs/*.log

# Stop with Ctrl+C (automatic cleanup)
```

## Documentation

- [Quickstart Guide](docs/quickstart.md) - Get started in 5 minutes
- [CLAUDE.md](CLAUDE.md) - Architecture and development guide

## Development

### Testing State Transitions

You can manually test state transitions by sending events to running machines:

```bash
# Start a machine (in one terminal)
statemachine examples/simple_worker/config/worker.yaml

# Send events to trigger transitions (in another terminal)
python -m statemachine_engine.database.cli send-event \
  --target simple_worker \
  --type new_job

# Check machine state
python -m statemachine_engine.database.cli machine-state --format json

# List recent events
python -m statemachine_engine.database.cli list-events \
  --target simple_worker \
  --limit 10
```

#### Testing Simple Worker Transitions

The simple_worker example has these transitions:
- `initializing` → `waiting` (event: `initialized`) - automatic on startup
- `waiting` → `processing` (event: `new_job`) - trigger with send-event
- `processing` → `completed` (event: `job_done`) - automatic after processing
- `completed` → `waiting` (event: `new_job`) - trigger to loop back
- `*` → `completed` (event: `stop`) - graceful shutdown from any state

**Test scenario:**
```bash
# Terminal 1: Start the worker
statemachine examples/simple_worker/config/worker.yaml


# Terminal 2: Test transitions
# 1. Trigger a job (waiting → processing → completed)
python -m statemachine_engine.database.cli send-event --target simple_worker --type new_job

# 2. Watch state changes in real-time
watch -n 1 'python -m statemachine_engine.database.cli machine-state'

# 3. Trigger another job (completed → waiting → processing → completed)
python -m statemachine_engine.database.cli send-event --target simple_worker --type new_job

# 4. Stop the machine (any state → completed)
python -m statemachine_engine.database.cli send-event --target simple_worker --type stop
```

#### How Event Delivery Works

When you use `send-event`, the CLI:
1. **Writes event to database** - Logs the event in the `machine_events` table (audit trail)
2. **Sends event via Unix socket** - Delivers the actual event with payload to `/tmp/statemachine-control-{machine_name}.sock`
3. **Machine processes event** - State machine receives event from socket and executes the transition immediately
4. **Broadcasts state change** - Updates are sent to `/tmp/statemachine-events.sock` → WebSocket → UI

**Important:** The `machine_events` database table is an **audit log only**. The actual event delivery happens via Unix sockets in real-time. Events are not read from the database - they're delivered directly through the socket.

**Unix Socket Paths:**
- Control sockets: `/tmp/statemachine-control-{machine_name}.sock` (receives events with full payload)
- Event socket: `/tmp/statemachine-events.sock` (broadcasts state changes to WebSocket server)
- WebSocket: `ws://localhost:3002/ws/events` (real-time updates to browser UI)

This dual approach (database + Unix socket) ensures:
- **Reliability**: Events are logged for audit (database persistence)
- **Speed**: Zero-latency event delivery via Unix socket (no polling)
- **Monitoring**: Real-time visibility via WebSocket broadcasting to UI

#### Available CLI Commands

```bash
# Machine management
python -m statemachine_engine.database.cli machine-state [--format json]

# Event management
python -m statemachine_engine.database.cli send-event --target <machine> --type <event> [--job-id <id>] [--payload <json>]
python -m statemachine_engine.database.cli list-events --target <machine> [--status pending|processed] [--limit N]

# Job queue management
python -m statemachine_engine.database.cli create-job --type <type> --data <json>
python -m statemachine_engine.database.cli list-jobs [--status pending|processing|completed|failed] [--limit N]
```

### Running Unit Tests

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
