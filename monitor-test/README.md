# Event Monitor Testing

Scripts to test the event monitoring system properly with log file redirection.

## Files

- `start-websocket.sh` - Start WebSocket server
- `start-worker.sh` - Start simple_worker state machine
- `run-monitor.sh` - Run event monitor
- `send-event.sh` - Send test event to worker
- `test-full.sh` - Full integration test
- `cleanup.sh` - Stop all processes and clean up

## Usage

```bash
# Start infrastructure
./start-websocket.sh
./start-worker.sh

# In another terminal, monitor events
./run-monitor.sh

# In another terminal, send test events
./send-event.sh
./send-event.sh
./send-event.sh

# Or run full automated test
./test-full.sh

# Clean up when done
./cleanup.sh
```

## Logs

All output goes to `logs/` directory:
- `logs/websocket.log` - WebSocket server output
- `logs/worker.log` - State machine output
- `logs/monitor.log` - Event monitor output
