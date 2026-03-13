#!/bin/bash
# Integrated startup script for state machine system
# Validates configs, generates diagrams, starts monitoring, and launches state machines

set -e

echo "🚀 Starting State Machine System..."
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down all services..."

    if [ ! -z "$WS_PID" ]; then
        kill $WS_PID 2>/dev/null || true
        echo "✓ WebSocket server stopped"
    fi

    if [ ! -z "$UI_PID" ]; then
        kill $UI_PID 2>/dev/null || true
        echo "✓ Web UI stopped"
    fi

    # Stop state machines gracefully
    pkill -f "statemachine" 2>/dev/null || true
    echo "✓ State machines stopped"

    echo "🏁 All services stopped"
    exit 0
}

trap cleanup INT TERM

# Check required commands
echo "🔍 Checking requirements..."
command -v python >/dev/null 2>&1 || { echo "❌ Python not found"; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "⚠️  curl not found (health checks will be skipped)"; }

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated"
    if [ -f "venv/bin/activate" ]; then
        echo "📦 Activating virtual environment..."
        source venv/bin/activate
    else
        echo "❌ No virtual environment found. Please run:"
        echo "   python -m venv venv"
        echo "   source venv/bin/activate"
        echo "   pip install -e ."
        exit 1
    fi
fi
echo "✓ Requirements check passed"
echo ""

# Validate configurations
echo "🔍 Validating state machine configurations..."
if [ -x "./scripts/validate-state-machines.py" ]; then
    # Find all YAML config files
    config_files=$(find examples -name "*.yaml" -type f 2>/dev/null)
    if [ -n "$config_files" ]; then
        if python ./scripts/validate-state-machines.py $config_files --quiet; then
            echo "✓ All configurations validated successfully"
        else
            echo "❌ Configuration validation failed"
            echo "   Please fix the errors above before starting"
            exit 1
        fi
    else
        echo "⚠️  No configuration files found in examples/"
        echo "   Skipping validation"
    fi
else
    echo "⚠️  Validator not found at ./scripts/validate-state-machines.py"
    echo "   Skipping validation (not recommended)"
fi
echo ""

# Generate FSM documentation
echo "📚 Generating FSM documentation..."
mkdir -p docs
mkdir -p docs/fsm-diagrams
for config in examples/**/config/*.yaml; do
    if [ -f "$config" ]; then
        echo "📄 Processing $config..."

        # Extract machine_name from YAML metadata
        machine_name=$(python -c "import yaml; c=yaml.safe_load(open('$config')); print(c.get('metadata', {}).get('machine_name', 'unknown'))" 2>/dev/null)
        if [ "$machine_name" = "unknown" ]; then
            # Fallback to filename if no metadata
            machine_name=$(basename "$config" .yaml)
        fi
        # Use CLI to generate both formats
        python -m statemachine_engine.tools.cli "$config" 2>&1 | grep -E "(✅|⚠️|❌|📁)" || {
            echo "  ⚠️  Failed to generate diagrams for $machine_name"
        }
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
python -m statemachine_engine.monitoring.websocket_server > logs/websocket-server.log 2>&1 &
WS_PID=$!

# Wait for WebSocket server to be ready
echo "⏳ Waiting for WebSocket server to start..."
for i in {1..10}; do
    sleep 1
    if command -v curl >/dev/null 2>&1 && curl -s http://localhost:3002/health > /dev/null 2>&1; then
        echo "✓ WebSocket server running on http://localhost:3002"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ WebSocket server failed to start after 10 seconds"
        if [ -f logs/websocket-server.log ]; then
            echo "📋 Last 20 lines of logs/websocket-server.log:"
            tail -20 logs/websocket-server.log
        fi
        exit 1
    fi
done
echo ""

# Start example state machines
echo "🤖 Starting example state machines..."
echo "  📊 Starting simple worker..."
statemachine examples/simple_worker/config/worker.yaml &
sleep 1
echo "✓ Simple worker started"
echo ""

# Start Web UI if Node.js is available
if command -v npm &> /dev/null; then
    echo "🖥️  Starting Web UI..."
    cd src/statemachine_engine/ui
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing UI dependencies..."
        npm install --silent
    fi
    npm start > ../../../logs/ui-server.log 2>&1 &
    UI_PID=$!
    cd ../../..
    echo "✓ Web UI starting on http://localhost:3001"
else
    echo "⚠️  Node.js not found, skipping Web UI"
    echo "   Install Node.js to enable the web interface"
fi
echo ""

echo "🎉 System started successfully!"
echo "================================"
echo "📊 WebSocket server: http://localhost:3002/health"
if [ ! -z "$UI_PID" ]; then
    echo "🌐 Web UI: http://localhost:3001"
fi
echo "📋 View logs: tail -f logs/*.log"
echo ""
echo "🛑 Press Ctrl+C to stop all services"
echo ""

# Keep script running
while true; do
    sleep 1
done
