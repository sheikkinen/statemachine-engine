#!/bin/bash
# Send a test event to simple_worker

cd /Users/sheikki/Documents/src/statemachine-engine

echo "Sending new_job event to simple_worker..."
python -m statemachine_engine.database.cli send-event --target simple_worker --type new_job

echo ""
echo "Event sent! Check the monitor output to see the state transitions."
