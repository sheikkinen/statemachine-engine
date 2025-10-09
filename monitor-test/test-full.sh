#!/bin/bash
# Full automated test of event monitoring system

cd /Users/sheikki/Documents/src/statemachine-engine/monitor-test

echo "=========================================="
echo "Event Monitor Integration Test"
echo "=========================================="
echo ""

# Clean up any existing processes
./cleanup.sh 2>/dev/null

echo "Step 1: Starting WebSocket server..."
./start-websocket.sh
if [ $? -ne 0 ]; then
    echo "❌ Failed to start WebSocket server"
    exit 1
fi
echo ""

echo "Step 2: Starting state machine..."
./start-worker.sh
if [ $? -ne 0 ]; then
    echo "❌ Failed to start state machine"
    ./cleanup.sh
    exit 1
fi
echo ""

echo "Step 3: Starting event monitor (10 seconds)..."
timeout 10 python -m statemachine_engine.tools.event_monitor > logs/monitor.log 2>&1 &
MONITOR_PID=$!
echo "Monitor started (PID: $MONITOR_PID)"
sleep 2
echo ""

echo "Step 4: Sending test events..."
for i in {1..3}; do
    echo "  Sending event $i..."
    ./send-event.sh > /dev/null 2>&1
    sleep 3
done
echo ""

echo "Step 5: Waiting for monitor to complete..."
wait $MONITOR_PID 2>/dev/null
echo ""

echo "=========================================="
echo "Test Results"
echo "=========================================="
echo ""

echo "Monitor output:"
echo "---"
cat logs/monitor.log
echo "---"
echo ""

echo "Worker log (last 20 lines):"
echo "---"
tail -20 logs/worker.log | grep -E "Received|-->|Action log"
echo "---"
echo ""

echo "WebSocket log (event-related):"
echo "---"
grep -E "Received event|Client connected|Client disconnected" logs/websocket.log | tail -10
echo "---"
echo ""

echo "Test complete! Check logs/ directory for full output."
echo ""
echo "To clean up: ./cleanup.sh"
