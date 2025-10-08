#!/bin/bash
# Production State Machine System Startup Script
# 
# This is a production-ready template for starting a complete state machine system.
# Copy this script to your project and customize for your specific needs.
#
# Features:
# - Virtual environment management
# - Configuration validation
# - FSM diagram generation
# - WebSocket monitoring server
# - Web UI (optional)
# - State machine launching
# - Graceful shutdown handling
#
# Usage:
#   1. Copy this script to your project root
#   2. Modify CONFIG_FILES and MACHINE_CONFIGS for your setup
#   3. Run: ./start-system.sh

set -e

# =============================================================================
# CONFIGURATION - Modify these for your project
# =============================================================================

# Configuration files to validate (space-separated)
CONFIG_FILES="config/worker.yaml config/controller.yaml"

# State machines to start (format: "config_file:machine_name")
MACHINE_CONFIGS=(
    "config/worker.yaml:worker"
    "config/controller.yaml:controller"
)

# Ports (customize if needed)
WEBSOCKET_PORT=8765
UI_PORT=3001

# =============================================================================
# SYSTEM STARTUP LOGIC
# =============================================================================

echo "🚀 Starting State Machine System..."
echo ""

# Cleanup function for graceful shutdown
cleanup() {
    echo ""
    echo "🛑 Shutting down all services..."
    
    # Stop WebSocket server
    if [ ! -z "$WS_PID" ]; then
        kill $WS_PID 2>/dev/null || true
        echo "✓ WebSocket server stopped"
    fi
    
    # Stop Web UI
    if [ ! -z "$UI_PID" ]; then
        kill $UI_PID 2>/dev/null || true
        echo "✓ Web UI stopped"
    fi
    
    # Stop state machines gracefully
    for config_machine in "${MACHINE_CONFIGS[@]}"; do
        machine_name="${config_machine#*:}"
        pkill -f "statemachine.*$machine_name" 2>/dev/null || true
    done
    echo "✓ State machines stopped"
    
    echo "🏁 All services stopped"
    exit 0
}

# Set up signal handlers
trap cleanup INT TERM

# Check required commands
echo "🔍 Checking requirements..."
command -v python >/dev/null 2>&1 || { echo "❌ Python not found"; exit 1; }
command -v statemachine >/dev/null 2>&1 || { echo "❌ statemachine command not found. Install statemachine-engine first."; exit 1; }

# Check if virtual environment should be activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated"
    if [ -f "venv/bin/activate" ]; then
        echo "📦 Activating virtual environment..."
        source venv/bin/activate
    elif [ -f ".venv/bin/activate" ]; then
        echo "📦 Activating virtual environment..."
        source .venv/bin/activate
    else
        echo "ℹ️  No virtual environment found (continuing without)"
    fi
fi
echo "✓ Requirements check passed"
echo ""

# Validate configurations
echo "🔍 Validating state machine configurations..."
if command -v statemachine-validate >/dev/null 2>&1; then
    if statemachine-validate --quiet $CONFIG_FILES; then
        echo "✓ All configurations validated successfully"
    else
        echo "❌ Configuration validation failed"
        echo "   Please fix the errors above before starting"
        exit 1
    fi
else
    echo "⚠️  statemachine-validate not found, skipping validation"
    echo "   Install with: pip install statemachine-engine"
fi
echo ""

# Generate FSM documentation
echo "📚 Generating FSM diagrams..."
mkdir -p docs/fsm-diagrams

for config_file in $CONFIG_FILES; do
    if [ -f "$config_file" ]; then
        echo "📄 Processing $config_file..."
        if command -v statemachine-diagrams >/dev/null 2>&1; then
            statemachine-diagrams "$config_file" 2>&1 | grep -E "(✅|⚠️|❌|📁)" || {
                echo "  ⚠️  Failed to generate diagrams for $config_file"
            }
        else
            echo "  ⚠️  statemachine-diagrams not found, skipping diagram generation"
        fi
    else
        echo "  ⚠️  Configuration file not found: $config_file"
    fi
done

if ls docs/fsm-diagrams/*/*.md 1> /dev/null 2>&1 || ls docs/fsm-diagrams/*/metadata.json 1> /dev/null 2>&1; then
    echo "✓ FSM documentation generated in docs/fsm-diagrams/"
else
    echo "⚠️  No FSM docs generated (UI diagrams will not display)"
fi
echo ""

# Create logs directory
mkdir -p logs

# Start WebSocket server
echo "🌐 Starting WebSocket monitoring server..."
if command -v statemachine-ui >/dev/null 2>&1; then
    python -m statemachine_engine.monitoring.websocket_server --port $WEBSOCKET_PORT > logs/websocket-server.log 2>&1 &
    WS_PID=$!
    
    # Wait for WebSocket server to be ready
    echo "⏳ Waiting for WebSocket server to start..."
    for i in {1..10}; do
        sleep 1
        if command -v curl >/dev/null 2>&1 && curl -s http://localhost:$WEBSOCKET_PORT/health > /dev/null 2>&1; then
            echo "✓ WebSocket server running on http://localhost:$WEBSOCKET_PORT"
            break
        fi
        if [ $i -eq 10 ]; then
            echo "❌ WebSocket server failed to start after 10 seconds"
            if [ -f logs/websocket-server.log ]; then
                echo "📋 Last 10 lines of logs/websocket-server.log:"
                tail -10 logs/websocket-server.log
            fi
            exit 1
        fi
    done
else
    echo "⚠️  statemachine-ui not found, skipping WebSocket server"
fi
echo ""

# Start state machines
echo "🤖 Starting state machines..."
for config_machine in "${MACHINE_CONFIGS[@]}"; do
    config_file="${config_machine%:*}"
    machine_name="${config_machine#*:}"
    
    if [ -f "$config_file" ]; then
        echo "  📊 Starting $machine_name from $config_file..."
        statemachine "$config_file" --machine-name "$machine_name" > "logs/${machine_name}.log" 2>&1 &
        sleep 1
        echo "✓ $machine_name started"
    else
        echo "❌ Configuration file not found: $config_file"
        exit 1
    fi
done
echo ""

# Start Web UI if Node.js is available
if command -v npm &> /dev/null && command -v statemachine-ui >/dev/null 2>&1; then
    echo "🖥️  Starting Web UI..."
    statemachine-ui --port $UI_PORT --no-websocket > logs/ui-server.log 2>&1 &
    UI_PID=$!
    echo "✓ Web UI starting on http://localhost:$UI_PORT"
else
    echo "⚠️  Node.js or statemachine-ui not found, skipping Web UI"
    echo "   Install Node.js and statemachine-engine to enable the web interface"
fi
echo ""

# System ready
echo "🎉 System started successfully!"
echo "================================"
if [ ! -z "$WS_PID" ]; then
    echo "📊 WebSocket server: http://localhost:$WEBSOCKET_PORT/health"
fi
if [ ! -z "$UI_PID" ]; then
    echo "🌐 Web UI: http://localhost:$UI_PORT"
fi
echo "📋 View logs: tail -f logs/*.log"
echo ""
echo "🧪 Test with:"
for config_machine in "${MACHINE_CONFIGS[@]}"; do
    machine_name="${config_machine#*:}"
    echo "   statemachine-db send-event --target $machine_name --type new_job"
done
echo ""
echo "🛑 Press Ctrl+C to stop all services"
echo ""

# Keep script running and wait for shutdown signal
while true; do
    sleep 1
done