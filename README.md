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

## Starting Services

The statemachine-engine system consists of several components that work together. Here's how to start each service:

### Complete System Startup (Recommended)

For development and testing, use the integrated startup script:

```bash
# Start everything at once
./scripts/start-system.sh

# This automatically starts:
# - WebSocket monitoring server
# - Web UI (if Node.js is available)
# - Example state machines
# - Generates FSM diagrams
```

### Individual Service Startup

For production or custom setups, start services individually:

#### 1. State Machine (Core Service)

```bash
# Basic usage
statemachine config/worker.yaml --machine-name my_worker

# With debug logging
statemachine config/worker.yaml --machine-name my_worker --debug

# Multiple machines (run in separate terminals)
statemachine config/controller.yaml --machine-name controller
statemachine config/worker.yaml --machine-name worker
```

#### 2. Web UI Server (Visualization)

```bash
# Start web UI with current project
statemachine-ui

# Start with custom project root
statemachine-ui --project-root /path/to/your/project

# Start on custom port
statemachine-ui --port 8080

# Skip WebSocket server (if already running)
statemachine-ui --no-websocket
```

**Access at:** http://localhost:3001

#### 3. WebSocket Server (Real-time Monitoring)

```bash
# Start WebSocket server
python -m statemachine_engine.monitoring.websocket_server

# Custom port
python -m statemachine_engine.monitoring.websocket_server --port 8765
```

**Endpoints:**
- WebSocket: `ws://localhost:8765/ws`
- Health check: `http://localhost:8765/health`

#### 4. Generate Diagrams

```bash
# Generate diagrams for UI
statemachine-diagrams config/worker.yaml

# Or use the alias
statemachine-fsm config/worker.yaml
```

### External Project Setup

If you're using statemachine-engine in your own project:

```bash
# In your project directory
cd /path/to/your/project

# 1. Generate diagrams for your config
statemachine-diagrams config/worker.yaml

# 2. Start UI with your project root
statemachine-ui --project-root $(pwd)

# 3. Start your state machine
statemachine config/worker.yaml --machine-name my_worker

# 4. Test with events
statemachine-db send-event --target my_worker --type new_job
```

### Database Commands

```bash
# Send events to trigger state transitions
statemachine-db send-event --target my_worker --type new_job

# Check machine states
statemachine-db machine-state

# List recent events
statemachine-db list-events --target my_worker --limit 10

# View job queue
statemachine-db list-jobs --status pending
```

### Service Dependencies

**Minimum Setup:**
- State machine: `statemachine config.yaml --machine-name name`

**With Monitoring:**
- State machine + WebSocket server
- Access real-time events at `ws://localhost:8765/ws`

**With Visualization:**
- State machine + WebSocket server + Web UI
- Full visual interface at `http://localhost:3001`

**Requirements:**
- Python 3.9+ (required)
- Node.js (optional, for Web UI)
- npm (optional, for Web UI dependencies)

### Troubleshooting

**Web UI can't find diagrams:**
```bash
# Ensure diagrams are generated in your project
statemachine-diagrams config/worker.yaml

# Start UI with correct project root
statemachine-ui --project-root $(pwd)
```

**Port conflicts:**
```bash
# Use custom ports
statemachine-ui --port 8080
python -m statemachine_engine.monitoring.websocket_server --port 9000
```

**Missing dependencies:**
```bash
# Install with all dependencies
pip install statemachine-engine[dev]

# Or install Node.js for Web UI
# macOS: brew install node
# Ubuntu: apt install nodejs npm
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

The WebSocket server provides real-time monitoring capabilities:

```bash
# Start WebSocket server
python -m statemachine_engine.monitoring.websocket_server

# Or use the integrated UI command (starts both WebSocket + Web UI)
statemachine-ui
```

**Endpoints:**
- WebSocket stream: `ws://localhost:8765/ws`
- Health check: `http://localhost:8765/health`

### Web UI

The package includes a comprehensive web UI for visualizing and monitoring state machines:

```bash
# Start Web UI (includes WebSocket server)
statemachine-ui

# Start with custom settings
statemachine-ui --port 3001 --project-root /path/to/project
```

**Features:**
- Real-time state machine visualization with Mermaid diagrams
- Live machine status updates and event streaming
- Interactive state transition monitoring
- Event history and activity logs
- Multi-machine coordination display

**Access:** http://localhost:3001

**Requirements:**
- Node.js (for Web UI functionality)
- Generated diagrams (run `statemachine-diagrams config.yaml` first)

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

**Production command (recommended):**
```bash
# Validate single config
statemachine-validate config/worker.yaml

# Validate all configs  
statemachine-validate config/*.yaml

# Strict mode (exit 1 on warnings)
statemachine-validate --strict config/*.yaml

# Quiet mode (errors only)
statemachine-validate --quiet config/*.yaml
```

**Development script (repository only):**
```bash
# For contributors/developers
./scripts/validate-state-machines.py config/worker.yaml
```

The validator checks:
- Event coverage (all events have transitions)
- Action emissions (success/error events exist)
- Orphaned/unreachable states
- Missing event declarations
- Self-loop patterns

### Production Templates

The `templates/` directory contains production-ready templates:

**Production startup script:**
```bash
# Copy template to your project
cp templates/start-system.sh ./
chmod +x start-system.sh

# Customize for your configs
vim start-system.sh  # Edit CONFIG_FILES and MACHINE_CONFIGS

# Run your system
./start-system.sh
```

See [templates/README.md](templates/README.md) for full customization guide.

### Start Worker

```bash
# Start with defaults
./scripts/start-worker.sh

# Specify config and machine name
./scripts/start-worker.sh examples/simple_worker/config/worker.yaml my_worker
```

### Development System Startup

**Development/testing script (repository only):**

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
statemachine-db send-event \
  --target simple_worker \
  --type new_job

# Check machine state
statemachine-db machine-state --format json

# List recent events
statemachine-db list-events \
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
statemachine-db send-event --target simple_worker --type new_job

# 2. Watch state changes in real-time
watch -n 1 'statemachine-db machine-state'

# 3. Trigger another job (completed → waiting → processing → completed)
statemachine-db send-event --target simple_worker --type new_job

# 4. Stop the machine (any state → completed)
statemachine-db send-event --target simple_worker --type stop
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

#### CLI Command Summary

The statemachine-engine package provides six main CLI commands:

```bash
statemachine         # Run state machines
statemachine-ui      # Start web UI server  
statemachine-db      # Database operations (events, jobs, state)
statemachine-diagrams # Generate FSM diagrams
statemachine-fsm     # Validate state machine configurations
statemachine-validate # Validate YAML configurations with detailed analysis
```

#### Available CLI Commands

```bash
# Machine management
statemachine-db machine-state [--format json]

# Event management
statemachine-db send-event --target <machine> --type <event> [--job-id <id>] [--payload <json>]
statemachine-db list-events --target <machine> [--status pending|processed] [--limit N]

# Job queue management
statemachine-db create-job --type <type> --data <json>
statemachine-db list-jobs [--status pending|processing|completed|failed] [--limit N]

# Configuration validation
statemachine-validate config/*.yaml [--strict] [--quiet] [--no-color]
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
