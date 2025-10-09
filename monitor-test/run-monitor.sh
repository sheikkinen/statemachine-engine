#!/bin/bash
# Run event monitor with log redirection

cd /Users/sheikki/Documents/src/statemachine-engine

echo "Starting event monitor..."
echo "Press Ctrl+C to stop"
echo ""

# Run monitor in foreground with output to both terminal and log
python -m statemachine_engine.tools.event_monitor "$@" 2>&1 | tee monitor-test/logs/monitor.log
