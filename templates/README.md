# Production Templates

This directory contains production-ready templates and samples for using statemachine-engine in your projects.

## Available Templates

### `start-system.sh` - Production Startup Script

A comprehensive production-ready startup script template that provides:

- **Configuration validation** using `statemachine-validate`
- **FSM diagram generation** for the web UI
- **WebSocket monitoring server** for real-time updates
- **Web UI server** (optional, requires Node.js)
- **Multiple state machine management**
- **Graceful shutdown handling** with proper cleanup
- **Logging** to separate files for each service
- **Virtual environment management**

**Usage:**

1. Copy the script to your project root:
   ```bash
   cp templates/start-system.sh ./
   chmod +x start-system.sh
   ```

2. Edit the configuration section at the top:
   ```bash
   # Configuration files to validate
   CONFIG_FILES="config/worker.yaml config/controller.yaml"
   
   # State machines to start (format: "config_file:machine_name")
   MACHINE_CONFIGS=(
       "config/worker.yaml:worker"
       "config/controller.yaml:controller"
   )
   ```

3. Run your system:
   ```bash
   ./start-system.sh
   ```

**Features:**
- Validates all configurations before starting
- Generates diagrams for web UI visualization  
- Starts WebSocket server for real-time monitoring
- Launches multiple state machines with proper logging
- Provides graceful shutdown (Ctrl+C)
- Shows test commands for your specific machines

**Requirements:**
- `statemachine-engine` package installed
- Configuration files in place
- Optional: Node.js for Web UI

## Customization

These templates are designed to be copied and modified for your specific needs:

- **Modify configuration paths** in the script variables
- **Add environment-specific setup** (database connections, API keys, etc.)
- **Customize logging locations** and formats
- **Add health checks** or monitoring integrations
- **Include your own cleanup procedures**

## Integration with CI/CD

The validation script can be integrated into your CI/CD pipeline:

```bash
# In your CI pipeline
statemachine-validate --strict config/*.yaml
```

This ensures configuration errors are caught before deployment.