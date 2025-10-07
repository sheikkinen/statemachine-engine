#!/bin/bash
# Start the WebSocket monitoring server
# Usage: ./scripts/start-monitoring.sh

set -e

echo "🌐 Starting WebSocket monitoring server..."

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated"
    if [ -f "venv/bin/activate" ]; then
        echo "📦 Activating virtual environment..."
        source venv/bin/activate
    else
        echo "❌ No virtual environment found"
        exit 1
    fi
fi

# Check dependencies
echo "🔍 Checking dependencies..."
python -c "import fastapi, uvicorn, websockets" 2>/dev/null || {
    echo "❌ Missing dependencies. Please install:"
    echo "   pip install fastapi uvicorn websockets"
    exit 1
}

# Create logs directory
mkdir -p logs

# Start server
echo "✓ Starting server on http://localhost:3002"
python -m statemachine_engine.monitoring.websocket_server

