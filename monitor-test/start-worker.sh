#!/bin/bash
# Start simple_worker state machine with log redirection

cd /Users/sheikki/Documents/src/statemachine-engine

echo "Starting simple_worker state machine..."
cd examples/simple_worker
python -m statemachine_engine.cli config/worker.yaml --machine-name simple_worker > ../../monitor-test/logs/worker.log 2>&1 &
WORKER_PID=$!

echo "State machine started (PID: $WORKER_PID)"
echo $WORKER_PID > ../../monitor-test/logs/worker.pid

# Wait for worker to initialize
sleep 3

# Check if control socket was created
if [ -e /tmp/statemachine-control-simple_worker.sock ]; then
    echo "✅ Control socket created: /tmp/statemachine-control-simple_worker.sock"
else
    echo "❌ Control socket not found!"
    exit 1
fi

echo "State machine ready!"
