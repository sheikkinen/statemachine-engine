#!/bin/bash
# Startup script for external projects using statemachine-engine
# Usage: ./start-external-project.sh /path/to/project config/worker.yaml machine_name

set -e

PROJECT_DIR="${1:-$(pwd)}"
CONFIG_FILE="${2:-config/worker.yaml}"
MACHINE_NAME="${3:-image_worker}"

echo "🚀 Starting State Machine System for External Project..."
echo "📁 Project: $PROJECT_DIR"
echo "⚙️  Config: $CONFIG_FILE"
echo "🤖 Machine: $MACHINE_NAME"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down all services..."
    
    pkill -f "statemachine examples/simple_worker" 2>/dev/null || true
    pkill -f "statemachine_engine.monitoring.websocket_server" 2>/dev/null || true
    pkill -f "node.*server.js" 2>/dev/null || true
    pkill -f "statemachine.*$MACHINE_NAME" 2>/dev/null || true
    
    echo "✅ System stopped"
    exit 0
}

trap cleanup INT TERM

# Change to project directory
cd "$PROJECT_DIR"

# Check if config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config file not found: $CONFIG_FILE"
    exit 1
fi

# Generate diagrams in project directory
echo "📚 Generating FSM diagrams..."
statemachine-ui "$CONFIG_FILE" || {
    echo "⚠️  Diagram generation failed, continuing anyway..."
}
echo ""

# Create logs directory
mkdir -p logs

# Start WebSocket server
echo "🌐 Starting WebSocket monitoring server..."
python -m statemachine_engine.monitoring.websocket_server > logs/websocket-server.log 2>&1 &
WS_PID=$!
sleep 2
echo "✓ WebSocket server started"
echo ""

# Start Web UI with project context
echo "🖥️  Starting Web UI..."
STATEMACHINE_UI_PATH=$(python -c "import statemachine_engine; import os; print(os.path.join(os.path.dirname(statemachine_engine.__file__), 'ui'))")

cd "$STATEMACHINE_UI_PATH"
# Set environment variable for project root
export PROJECT_ROOT="$PROJECT_DIR"
node server.js > "$PROJECT_DIR/logs/ui-server.log" 2>&1 &
UI_PID=$!
cd "$PROJECT_DIR"
sleep 2
echo "✓ Web UI started on http://localhost:3001"
echo ""

# Start the state machine
echo "🤖 Starting state machine: $MACHINE_NAME..."
statemachine "$CONFIG_FILE" --machine-name "$MACHINE_NAME" --debug &
MACHINE_PID=$!
sleep 1
echo "✓ State machine started"
echo ""

echo "🎉 System started successfully!"
echo "================================"
echo "🌐 Web UI: http://localhost:3001"
echo "📊 WebSocket: ws://localhost:8765"
echo "📋 View logs: tail -f logs/*.log"
echo ""
echo "🧪 Test with:"
echo "   python -m statemachine_engine.database.cli send-event --target $MACHINE_NAME --type new_job"
echo ""
echo "🛑 Press Ctrl+C to stop all services"
echo ""

# Keep script running
while true; do
    sleep 1
done