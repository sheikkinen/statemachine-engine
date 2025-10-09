#!/bin/bash
# Clean up all processes and sockets

cd /Users/sheikki/Documents/src/statemachine-engine/monitor-test

echo "Cleaning up..."

# Kill WebSocket server
if [ -f logs/websocket.pid ]; then
    WEBSOCKET_PID=$(cat logs/websocket.pid)
    if kill -0 $WEBSOCKET_PID 2>/dev/null; then
        echo "Stopping WebSocket server (PID: $WEBSOCKET_PID)..."
        kill $WEBSOCKET_PID
        rm logs/websocket.pid
    fi
fi

# Kill worker
if [ -f logs/worker.pid ]; then
    WORKER_PID=$(cat logs/worker.pid)
    if kill -0 $WORKER_PID 2>/dev/null; then
        echo "Stopping state machine (PID: $WORKER_PID)..."
        kill $WORKER_PID
        rm logs/worker.pid
    fi
fi

# Clean up any stray processes
pkill -f "statemachine_engine.monitoring.websocket_server" 2>/dev/null
pkill -f "statemachine_engine.cli.*simple_worker" 2>/dev/null
pkill -f "statemachine_engine.tools.event_monitor" 2>/dev/null

# Clean up sockets
rm -f /tmp/statemachine-events.sock 2>/dev/null
rm -f /tmp/statemachine-control-simple_worker.sock 2>/dev/null

echo "Cleanup complete!"
