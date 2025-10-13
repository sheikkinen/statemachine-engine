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

#### ⚠️ Breaking Change in v1.0.3: add-job Command

The `add-job` command has been redesigned to be fully generic. **Update your scripts:**

```bash
# OLD (v1.0.2 and earlier) - DEPRECATED
statemachine-db add-job job123 \
  --type face_processing \
  --input-image photo.jpg \
  --prompt "enhance faces"

# NEW (v1.0.3+) - Use --payload for all custom data
statemachine-db add-job job123 \
  --type face_processing \
  --input-file photo.jpg \
  --payload '{"prompt": "enhance faces"}'
```

**Quick Migration:**
- Remove: `--input-image`, `--prompt`, `--pony-prompt`, `--flux-prompt`, `--padding-factor`, `--mask-padding-factor`
- Use: `--input-file` (for file paths) and `--payload '{"key": "value"}'` (for all other data)
- `--type` now accepts any string (no hardcoded choices)

```bash
# Add jobs to the queue
statemachine-db add-job job_001 \
  --type image_processing \
  --payload '{"input": "image.jpg", "output": "result.png"}'

# Send events to trigger state transitions
statemachine-db send-event --target my_worker --type new_job

# Check machine states
statemachine-db machine-state

# List recent events
statemachine-db list-events --target my_worker --limit 10

# View job queue
statemachine-db list --status pending

# View specific job details
statemachine-db details <job-id>
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

### log - Activity Logging

Log messages that appear in the Web UI's activity log panel.

**YAML Configuration:**
```yaml
actions:
  processing:
    - type: log
      message: "🔄 Processing job {id}"
      level: info        # Optional: info (default), error, success
      success: continue  # Optional: event to emit on success
```

**Features:**
- **Variable substitution**: `{id}`, `{job_id}`, `{current_state}`, `{machine_name}`
- **Event payload access**: `{event_data.payload.field_name}`
- **Log levels**: `info` (blue), `error` (red), `success` (green)
- **Real-time display**: Messages appear instantly in Web UI

**Examples:**
```yaml
# Simple info message
- type: log
  message: "Worker ready - waiting for jobs"

# With context variables
- type: log
  message: "Processing job {id} in state {current_state}"
  level: info

# Error logging
- type: log
  message: "❌ Job {id} failed: {error_message}"
  level: error

# Success notification
- type: log
  message: "✅ Completed {id} - generated {output_count} results"
  level: success
```

### bash - Execute Shell Commands

Execute shell commands with timeout and error handling.

**YAML Configuration:**
```yaml
- type: bash
  description: "Process the job"
  command: "python process.py --input {input_file}"
  timeout: 30
  success: job_done
  error: job_failed
```

### Other Built-In Actions

- **check_database_queue**: Check job queue for pending jobs
- **check_machine_state**: Monitor machine states
- **clear_events**: Clean up processed events
- **send_event**: Send events to other machines

See `examples/` directory for complete working examples.

## Custom Actions

### Creating Custom Actions

Extend the framework with your own actions by inheriting from `BaseAction`:

**1. Create action file** (e.g., `my_custom_action.py`):

```python
from statemachine_engine.actions import BaseAction

class MyCustomAction(BaseAction):
    async def execute(self, context):
        # Access config parameters from YAML
        param_value = self.config.get('params', {}).get('my_param')

        # Access execution context (job_id, machine_name, etc.)
        job_id = context.get('job_id')
        machine = self.get_machine_name(context)

        # Your custom logic
        self.logger.info(f"Processing {job_id} on {machine}")

        # Return event name to trigger next transition
        return self.config.get('params', {}).get('success', 'success')
```

**2. Place in your project's actions directory**:

```bash
my_project/
├── actions/
│   ├── my_custom_action.py
│   └── another_action.py
└── config/
    └── worker.yaml
```

**3. Use in YAML configuration**:

```yaml
actions:
  - type: my_custom  # Maps to my_custom_action.py → MyCustomAction class
    params:
      my_param: "value"
      success: job_done
```

**4. Run with custom actions directory**:

```bash
# Use --actions-dir to specify your custom actions directory
statemachine config/worker.yaml \
  --machine-name my_worker \
  --actions-dir ./actions

# Supports absolute and relative paths
statemachine config/worker.yaml \
  --machine-name my_worker \
  --actions-dir /path/to/my_project/actions

# Supports ~ (home directory) expansion
statemachine config/worker.yaml \
  --machine-name my_worker \
  --actions-dir ~/projects/my_worker/actions
```

### Action Discovery

The `ActionLoader` automatically discovers actions following these conventions:

- **File naming**: `{action_type}_action.py`
- **Class naming**: `{ActionType}Action` (PascalCase)
- **Example**: `my_custom_action.py` → `MyCustomAction` class
- **YAML reference**: `type: my_custom`

**Discovery Locations:**
- **With `--actions-dir`**: Discovers from BOTH custom directory AND built-in actions
- **Without `--actions-dir`**: Discovers only from the installed package's `actions/` directory

**Action Precedence:**
- Custom actions can override built-in actions with the same name
- Custom actions take precedence when name conflicts occur
- Both custom and built-in actions are available in the same workflow

**Benefits of `--actions-dir`:**
- ✅ No package installation required for custom actions
- ✅ Fast iteration: edit action → test immediately
- ✅ Simple project structure without setup.py/pyproject.toml
- ✅ Keep actions alongside your YAML configs where they belong
- ✅ Use both custom actions AND built-in actions (bash, log, send_event, etc.)
- ✅ Override built-in actions with custom implementations when needed

## Variable Interpolation

**New in v0.1.0:** The engine now provides automatic variable interpolation at the engine level, making context data available to all actions consistently.

### How It Works

The engine automatically substitutes `{variable}` placeholders in action configurations before passing them to actions. This happens transparently for all action types (built-in and custom).

### Supported Variable Types

#### Simple Variables
Access any value in the context dictionary:

```yaml
actions:
  processing:
    - type: log
      message: "Processing job {job_id} with status {status}"
    
    - type: bash
      command: "python process.py --id {job_id} --state {current_state}"
```

**Available context variables:**
- `{job_id}` - Current job ID
- `{id}` - Alias for job_id
- `{current_state}` - Current state machine state
- `{machine_name}` - Name of the current machine
- `{status}` - Job status
- Any custom variables added by actions to context

#### Nested Variables
Access nested data using dot notation:

```yaml
actions:
  relaying:
    - type: bash
      command: "process {event_data.payload.job_id}"
      
    - type: log
      message: "Input: {event_data.payload.input_file}, Prompt: {event_data.payload.user_prompt}"
      
    - type: send_event
      target_machine: worker
      event_type: task_request
      payload:
        file: "{event_data.payload.input_image}"
        user: "{event_data.payload.user.name}"
        priority: "{event_data.payload.metadata.priority}"
```

**Common nested paths:**
- `{event_data.payload.*}` - Event payload fields
- `{event_data.event_name}` - The event that triggered this action
- `{current_job.data.*}` - Job data fields (if job_model is used)

### Custom Actions and Context Modification

Custom actions can now modify the context dictionary, and those changes will be visible to subsequent actions through variable interpolation:

```python
# custom_extract_action.py
class CustomExtractAction(BaseAction):
    async def execute(self, context):
        # Extract data from event payload
        payload = context['event_data']['payload']
        
        # Add to context for subsequent actions
        context['user_id'] = payload.get('user_id')
        context['file_path'] = payload.get('input_file')
        context['processing_mode'] = 'fast'
        
        return 'extracted'
```

```yaml
# worker.yaml
actions:
  extracting:
    - type: custom_extract
      success: extracted
    
    # These actions now see the extracted variables
    - type: log
      message: "Processing file {file_path} for user {user_id} in {processing_mode} mode"
    
    - type: bash
      command: "process --user {user_id} --file {file_path} --mode {processing_mode}"
```

### Benefits

- **✅ No repetitive references**: Extract once, use everywhere (no more `{event_data.payload.field}` everywhere)
- **✅ Cleaner YAML**: Shorter, more readable action configurations
- **✅ Type safety**: Values are automatically converted to strings
- **✅ Consistent behavior**: All actions (built-in and custom) use the same interpolation
- **✅ Unknown placeholders preserved**: If a variable doesn't exist, the placeholder remains for debugging
- **✅ Special characters supported**: Handles spaces, quotes, and special characters correctly

### Advanced Examples

**Combining static and dynamic values:**
```yaml
- type: bash
  command: "convert {input_file} -resize {width}x{height} {output_file}"
  params:
    output_file: "/tmp/{job_id}_resized.png"  # Interpolated
    width: "800"                                # Static
```

**Deeply nested structures:**
```yaml
- type: send_event
  target_machine: logger
  event_type: log_activity
  payload:
    user:
      id: "{event_data.payload.user.id}"
      name: "{event_data.payload.user.name}"
    action: "{event_data.payload.metadata.action}"
    timestamp: "{current_timestamp}"
```

**List processing:**
```yaml
- type: multi_step
  steps:
    - "step1 {job_id}"
    - "step2 {output_dir}/{file_name}"
    - "step3 {status}"
```

### Implementation Details

The interpolation happens in the `StateMachineEngine._interpolate_config()` method before actions are executed. This ensures:
- All action types benefit automatically
- Custom actions don't need to implement their own interpolation
- Variables are resolved consistently across the entire workflow
- Performance is optimized (single pass per action config)

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

### Event Payload Forwarding

The `send_event` action supports powerful payload forwarding and transformation capabilities for multi-machine orchestration.

#### Automatic JSON Parsing

External event payloads sent as JSON strings are automatically parsed to dictionaries:

```bash
# Send event via CLI with JSON payload
statemachine-db send-event \
  --target worker \
  --type process_task \
  --payload '{"file": "image.png", "user_id": 123}'
```

The receiving machine automatically parses the JSON string to a dictionary, making fields accessible in actions.

#### Extracting Specific Fields

Extract and forward specific fields from received payloads:

```yaml
# controller.yaml
relaying_to_worker:
  - type: send_event
    target_machine: worker
    event_type: task_request
    payload:
      input_file: "{event_data.payload.file}"
      user_id: "{event_data.payload.user_id}"
      priority: "high"  # Add static values
    success: relay_complete
```

#### Nested Field Access

Access nested fields using dot notation:

```yaml
# Extract nested data
relaying_user_info:
  - type: send_event
    target_machine: logger
    event_type: log_activity
    payload:
      user_id: "{event_data.payload.user.id}"
      user_name: "{event_data.payload.user.name}"
      action: "{event_data.payload.metadata.action}"
```

#### Forwarding Entire Payloads

Forward the complete payload without modification:

```yaml
# Simple relay pattern
relaying:
  - type: send_event
    target_machine: downstream_worker
    event_type: relay_complete
    payload: "{event_data.payload}"  # Forward entire dict
    success: relay_sent
```

#### Multi-Machine Orchestration Example

A complete controller pattern that relays data between multiple workers:

```yaml
# controller.yaml
metadata:
  name: "Image Processing Controller"
  machine_name: controller

initial_state: waiting

transitions:
  # Receive from generator
  - from: waiting
    to: relaying_to_processor
    event: image_generated

  # Relay to face processor
  - from: relaying_to_processor
    to: waiting_for_processor
    event: start_relay

  # Receive from processor
  - from: waiting_for_processor
    to: relaying_to_finalizer
    event: processing_complete

  # Relay to finalizer
  - from: relaying_to_finalizer
    to: waiting
    event: relay_complete

actions:
  # Extract specific fields and relay
  relaying_to_processor:
    - type: send_event
      target_machine: face_processor
      event_type: process_faces
      payload:
        base_image: "{event_data.payload.generated_image}"
        job_id: "{event_data.payload.job_id}"
        style: "{event_data.payload.face_style}"
      success: start_relay
  
  # Forward complete result
  relaying_to_finalizer:
    - type: send_event
      target_machine: finalizer
      event_type: finalize_image
      payload: "{event_data.payload}"  # Forward everything
      success: relay_complete
```

#### Benefits of Payload Forwarding

- **Performance**: 10-50x faster than bash subprocess workarounds
- **Type Safety**: Automatic JSON parsing with error handling
- **Clarity**: Explicit field extraction shows data dependencies
- **Flexibility**: Mix extracted fields with static values
- **Simplicity**: No custom bash actions needed for relay patterns

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

## Tools & Utilities

### Validate Configurations

```bash
statemachine-validate config/worker.yaml         # Single file
statemachine-validate config/*.yaml              # All configs
statemachine-validate --strict config/*.yaml     # Fail on warnings
```

Checks: event coverage, action emissions, unreachable states, self-loops

### Monitor Real-Time Events

```bash
statemachine-events                              # All machines, human format
statemachine-events --machine simple_worker      # Filter by machine
statemachine-events --format json > events.log   # JSON output
statemachine-events --duration 60                # Time limit
```

Connects to `/tmp/statemachine-events.sock` to display all state changes in real-time

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

### Migrating add-job Scripts (v1.0.2 → v1.0.3)

If you have existing scripts using `add-job`, update them as follows:

```bash
# Pattern 1: Image processing with prompt
# OLD:
add-job $JOB_ID --type face_processing --input-image "$IMAGE" --prompt "$PROMPT"
# NEW:
add-job $JOB_ID --type face_processing --input-file "$IMAGE" --payload "{\"prompt\":\"$PROMPT\"}"

# Pattern 2: Image generation with multiple prompts
# OLD:
add-job $JOB_ID --type pony_flux --pony-prompt "$PONY" --flux-prompt "$FLUX"
# NEW:
add-job $JOB_ID --type pony_flux --payload "{\"pony_prompt\":\"$PONY\",\"flux_prompt\":\"$FLUX\"}"

# Pattern 3: With padding factors
# OLD:
add-job $JOB_ID --type face_processing --input-image "$IMG" --padding-factor 1.5 --mask-padding-factor 1.2
# NEW:
add-job $JOB_ID --type face_processing --input-file "$IMG" --payload '{"padding_factor":1.5,"mask_padding_factor":1.2}'

# Pattern 4: Custom job types (now supported!)
# NEW: You can now use ANY job type string
add-job $JOB_ID --type custom_workflow --payload '{"config":"value"}'
```

**Helper function for easy migration:**
```bash
# Add to your scripts for backward compatibility
add_job_v103() {
    local job_id="$1"
    local job_type="$2"
    local input_file="$3"
    local payload="$4"
    
    statemachine-db add-job "$job_id" \
        --type "$job_type" \
        ${input_file:+--input-file "$input_file"} \
        ${payload:+--payload "$payload"}
}

# Usage:
add_job_v103 "job123" "image_processing" "/path/to/image.jpg" '{"prompt":"enhance"}'
```

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

#### CLI Commands

```bash
statemachine          # Run state machines
statemachine-ui       # Web UI server with real-time visualization
statemachine-db       # Database operations (events, jobs, state)
statemachine-diagrams # Generate FSM diagrams from YAML
statemachine-validate # Validate YAML configurations
statemachine-events   # Monitor real-time events from Unix socket
```

#### Database Commands

```bash
# Events
statemachine-db send-event --target <machine> --type <event>
statemachine-db list-events --target <machine> --limit 10

# Send events with real-time UI updates (NEW)
# Sends to both database AND Unix socket for instant UI display
statemachine-db send-event --target ui --type activity_log \
  --payload '{"message": "Task completed", "level": "SUCCESS"}'

# Custom source attribution for UI display
statemachine-db send-event --target ui --type activity_log \
  --source my_tool --payload '{"message": "Processing...", "level": "INFO"}'

# Send to state machines (goes to database + machine control socket + WebSocket UI)
statemachine-db send-event --target worker1 --type custom_event \
  --job-id job123 --payload '{"data": "value"}'

# Jobs (NEW in v1.0.3: Fully generic job creation)
# Add jobs with any job type and custom JSON payload
statemachine-db add-job job_001 \
  --type image_processing \
  --payload '{"input": "image.jpg", "config": {"quality": 95}}'

# Add job with machine type (routes to specific worker type)
statemachine-db add-job job_002 \
  --type video_transcode \
  --machine-type video_worker \
  --payload '{"source": "video.mp4", "format": "h264"}'

# Add job with input file reference
statemachine-db add-job job_003 \
  --type document_convert \
  --input-file /path/to/document.pdf \
  --payload '{"output_format": "docx"}'

# Add job with complex nested data
statemachine-db add-job ml_batch_001 \
  --type ml_inference \
  --payload '{
    "model": "resnet50",
    "input": {"image": "photo.jpg"},
    "options": {"batch_size": 32, "gpu": true}
  }'

# List and filter jobs
statemachine-db list --status pending
statemachine-db list --type image_processing --limit 20
statemachine-db list --status completed

# Job details
statemachine-db details <job-id>
statemachine-db details test_job_001

# State
statemachine-db machine-state

# State Transition History
statemachine-db transition-history                    # Show all state transitions
statemachine-db transition-history --machine worker1  # Filter by machine
statemachine-db transition-history --hours 24         # Last 24 hours
statemachine-db transition-history --limit 50         # Limit results
statemachine-db transition-history --format json      # JSON output

# Error/Exception History
statemachine-db error-history                         # Show all errors
statemachine-db error-history --machine worker1       # Filter by machine
statemachine-db error-history --hours 1               # Last hour
statemachine-db error-history --format json           # JSON output
```

**Real-time Event Delivery (NEW in v0.0.20):**
- `send-event` now delivers events to the Web UI instantly via Unix socket
- Activity logs sent via CLI appear immediately in the UI (no refresh needed)
- Requires WebSocket server (`statemachine-ui`) to be running
- Falls back gracefully to database-only if server unavailable

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

**Current Test Status:** 143 tests total (136 passing, 0 failing, 7 skipped) - 100% pass rate ✅

**New in v0.0.18+:**
- Comprehensive exception handling tests for realtime events
- CLI history command tests (transition-history, error-history)
- Engine error emission tests
- Real-time socket delivery tests for send-event CLI (v0.0.20)

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
