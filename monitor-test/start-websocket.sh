#!/bin/bash
# Start WebSocket server with log redirection

cd /Users/sheikki/Documents/src/statemachine-engine

echo "Starting WebSocket server..."
python -m statemachine_engine.monitoring.websocket_server > monitor-test/logs/websocket.log 2>&1 &
WEBSOCKET_PID=$!

echo "WebSocket server started (PID: $WEBSOCKET_PID)"
echo $WEBSOCKET_PID > monitor-test/logs/websocket.pid

# Wait for server to be ready
sleep 2

# Check if socket was created
if [ -e /tmp/statemachine-events.sock ]; then
    echo "✅ Event broadcast socket created: /tmp/statemachine-events.sock"
else
    echo "❌ Event broadcast socket not found!"
    exit 1
fi

# Check if port is listening
if lsof -i :3002 > /dev/null 2>&1; then
    echo "✅ WebSocket server listening on port 3002"
else
    echo "❌ WebSocket server not listening on port 3002"
    exit 1
fi

echo "WebSocket server ready!"
