#!/bin/bash
# Quick test - just monitor events live

cd /Users/sheikki/Documents/src/statemachine-engine/monitor-test

echo "Quick Event Monitor Test"
echo "========================"
echo ""
echo "This will:"
echo "1. Start WebSocket server (if not running)"
echo "2. Start simple_worker (if not running)"
echo "3. Run event monitor"
echo ""
echo "In another terminal, run: ./send-event.sh"
echo "Press Ctrl+C to stop monitoring"
echo ""
read -p "Press Enter to continue..."

# Check if WebSocket server is running
if ! lsof -i :3002 > /dev/null 2>&1; then
    echo "Starting WebSocket server..."
    ./start-websocket.sh
    echo ""
fi

# Check if worker is running
if [ ! -e /tmp/statemachine-control-simple_worker.sock ]; then
    echo "Starting state machine..."
    ./start-worker.sh
    echo ""
fi

# Run monitor
./run-monitor.sh
