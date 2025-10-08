#!/bin/bash
# Start controller and worker machines in parallel

echo "Starting controller and worker..."
statemachine config/controller.yaml --machine-name controller &
CONTROLLER_PID=$!

statemachine config/worker.yaml --machine-name worker &
WORKER_PID=$!

echo "Controller PID: $CONTROLLER_PID"
echo "Worker PID: $WORKER_PID"
echo "Press Ctrl+C to stop both machines"

# Wait for both processes
wait
