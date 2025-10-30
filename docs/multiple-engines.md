# Running Multiple State Machine Engines

The hardcoded address issue has been **RESOLVED** in version 1.0.63!

## What was fixed

Previously, multiple engines couldn't run simultaneously because these addresses were hardcoded:
- Event socket: `/tmp/statemachine-events.sock`
- WebSocket server: `127.0.0.1:3002`
- Control socket prefix: `/tmp/statemachine-control`

## New CLI Options

### State Machine Engine
```bash
python -m statemachine_engine.cli config.yaml [options]

Options:
  --event-socket-path EVENT_SOCKET_PATH
                        Custom event socket path (default: /tmp/statemachine-events.sock)
  --control-socket-prefix CONTROL_SOCKET_PREFIX
                        Custom control socket prefix (default: /tmp/statemachine-control)
```

### WebSocket Server
```bash
python -m statemachine_engine.monitoring.websocket_server [options]

Options:
  --host HOST           Host to bind to (default: 127.0.0.1)
  --port PORT           Port to bind to (default: 3002)
  --event-socket-path EVENT_SOCKET_PATH
                        Path to event socket (default: /tmp/statemachine-events.sock)
```

## Example: Running Multiple Engines

### Terminal 1 - Engine 1
```bash
python -m statemachine_engine.cli engine1_config.yaml \
    --event-socket-path /tmp/engine1-events.sock \
    --control-socket-prefix /tmp/engine1-control
```

### Terminal 2 - Engine 2  
```bash
python -m statemachine_engine.cli engine2_config.yaml \
    --event-socket-path /tmp/engine2-events.sock \
    --control-socket-prefix /tmp/engine2-control
```

### Terminal 3 - Monitor Engine 1
```bash
python -m statemachine_engine.monitoring.websocket_server \
    --port 3002 \
    --event-socket-path /tmp/engine1-events.sock
```

### Terminal 4 - Monitor Engine 2
```bash
python -m statemachine_engine.monitoring.websocket_server \
    --port 3003 \
    --event-socket-path /tmp/engine2-events.sock
```

## Web Interfaces

- Engine 1 monitoring: http://localhost:3002
- Engine 2 monitoring: http://localhost:3003

## Backward Compatibility

All default values remain the same, so existing scripts continue to work unchanged.

## Version

This fix is available in **statemachine-engine v1.0.63**.