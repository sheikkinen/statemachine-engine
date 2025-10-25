# WebSocket Communication System

## Overview

The state machine engine uses a **dual-socket architecture** for real-time event streaming:

1. **Unix Domain Socket** - State machines → WebSocket server (IPC)
2. **WebSocket** - WebSocket server → Browser clients (network)

This decouples state machine execution from web client connectivity, allowing machines to run independently while providing real-time monitoring capabilities.

## Architecture Diagram

```
┌─────────────────┐
│ State Machine 1 │──┐
└─────────────────┘  │
                     │  Unix DGRAM Socket
┌─────────────────┐  │  /tmp/statemachine-events.sock
│ State Machine 2 │──┼──────────────────────┐
└─────────────────┘  │                      │
                     │                      ▼
┌─────────────────┐  │              ┌──────────────────┐
│ State Machine N │──┘              │  WebSocket       │
└─────────────────┘                 │  Server          │
                                    │  (Port 3002)     │
                                    └──────────────────┘
                                            │
                                            │ WebSocket Protocol
                                            │ ws://localhost:3002/ws/events
                                            │
                                    ┌───────┴──────┐
                                    │              │
                                    ▼              ▼
                            ┌──────────────┐ ┌──────────────┐
                            │  Browser 1   │ │  Browser 2   │
                            └──────────────┘ └──────────────┘
```

---

## Unix Domain Socket Communication

### Purpose
State machines send events to the WebSocket server without blocking or requiring network connectivity.

### Socket Details
- **Type**: `SOCK_DGRAM` (datagram, connectionless)
- **Path**: `/tmp/statemachine-events.sock`
- **Protocol**: JSON over Unix socket
- **Direction**: State machines → WebSocket server (one-way)

### Why DGRAM?
- **Non-blocking**: State machines don't wait for server acknowledgment
- **Fire-and-forget**: If server is down, machines continue running
- **No connection overhead**: Each event is independent
- **Simple**: No connection management required

### Message Format
```json
{
  "type": "state_change",
  "machine_id": "worker-123",
  "state": "processing",
  "timestamp": 1729845678.123,
  "data": {
    "job_id": "task-456",
    "progress": 50
  }
}
```

### Server-Side Listener

The WebSocket server runs an async task that continuously listens on the Unix socket:

```python
async def unix_socket_listener():
    """Listen for events from state machines on Unix socket"""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(SOCKET_PATH)
    sock.setblocking(False)
    
    while True:
        try:
            # Non-blocking receive with timeout
            data, addr = await asyncio.wait_for(
                asyncio.get_event_loop().sock_recvfrom(sock, 4096),
                timeout=1.0
            )
            
            event = json.loads(data.decode('utf-8'))
            
            # Broadcast to all connected WebSocket clients
            await broadcaster.broadcast(event)
            
        except asyncio.TimeoutError:
            continue  # No data, keep listening
```

### Client-Side Sender (State Machines)

State machines send events via the `send_event()` function:

```python
def send_event(event_type: str, machine_id: str, **kwargs):
    """Send event to WebSocket server via Unix socket"""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        
        event = {
            'type': event_type,
            'machine_id': machine_id,
            'timestamp': time.time(),
            **kwargs
        }
        
        message = json.dumps(event).encode('utf-8')
        sock.sendto(message, SOCKET_PATH)
        sock.close()
        
    except Exception as e:
        # Fail silently - monitoring is optional
        logger.debug(f"Failed to send event: {e}")
```

**Key Point**: If the WebSocket server is not running, state machines continue executing normally. Events are simply dropped.

---

## WebSocket Broadcasting

### Purpose
Distribute real-time events to multiple browser clients simultaneously.

### WebSocket Details
- **Protocol**: WebSocket (RFC 6455)
- **URL**: `ws://localhost:3002/ws/events`
- **Framework**: FastAPI/Starlette
- **Direction**: Server → Clients (one-way for events, two-way for control)

### Broadcaster Pattern

The server maintains a set of connected WebSocket clients and broadcasts events to all:

```python
class Broadcaster:
    def __init__(self):
        self.connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Register new WebSocket client"""
        await websocket.accept()
        self.connections.add(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        """Unregister WebSocket client"""
        self.connections.discard(websocket)
    
    async def broadcast(self, event: dict):
        """Send event to all connected clients"""
        # Pre-serialize JSON to avoid blocking (v1.0.26 fix)
        event_json, success = safe_json_dumps_compact(event)
        
        if not success:
            logger.error("Failed to serialize broadcast event")
            return
        
        # Send to all clients with timeout protection
        dead_connections = set()
        
        for ws in self.connections:
            try:
                # Use send_text() with pre-serialized JSON
                # (NOT send_json() which blocks on serialization)
                await asyncio.wait_for(
                    ws.send_text(event_json),
                    timeout=2.0
                )
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                dead_connections.add(ws)
        
        # Clean up failed connections
        self.connections -= dead_connections
```

### Critical Performance Fix (v1.0.26)

**Problem**: Starlette's `WebSocket.send_json()` calls `json.dumps()` **synchronously** before awaiting:

```python
# Starlette's implementation (BLOCKING!)
async def send_json(self, data):
    text = json.dumps(data)  # ← Blocks event loop here!
    await self.send({"type": "websocket.send", "text": text})
```

**Solution**: Pre-serialize JSON, then use `send_text()`:

```python
# Our fix (NON-BLOCKING)
event_json = json.dumps(event, separators=(",", ":"))  # Serialize first
await websocket.send_text(event_json)  # Then send pre-serialized string
```

This reduced broadcast time from **15-40 seconds** to **~2ms** for large state objects.

---

## Ping/Pong Keepalive System

### Purpose
Prevent WebSocket connections from timing out due to inactivity and detect dead connections.

### Ping/Pong Flow

```
Server                                    Client
  │                                         │
  │  {"type": "ping", "timestamp": ...}     │
  │────────────────────────────────────────>│
  │                                         │
  │  {"type": "pong"}                       │
  │<────────────────────────────────────────│
  │                                         │
  │  (wait 10 seconds)                      │
  │                                         │
  │  {"type": "ping", "timestamp": ...}     │
  │────────────────────────────────────────>│
  │                                         │
```

### Server-Side Implementation

Each WebSocket connection has a dedicated keepalive task:

```python
async def send_keepalive(websocket: WebSocket, client_id: int):
    """Send periodic pings to keep connection alive"""
    ping_interval = 10  # seconds
    
    try:
        while True:
            await asyncio.sleep(ping_interval)
            
            ping_data = {
                'type': 'ping',
                'timestamp': time.time()
            }
            
            # Pre-serialize to avoid blocking (v1.0.26 fix)
            ping_json, success = safe_json_dumps_compact(ping_data)
            
            if success:
                await websocket.send_text(ping_json)
            else:
                logger.error(f"Failed to serialize ping for client {client_id}")
                break
                
    except Exception as e:
        logger.warning(f"Keepalive failed for client {client_id}: {e}")
```

The keepalive task runs as a background task for each connection:

```python
@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    client_id = id(websocket)
    
    await broadcaster.connect(websocket)
    
    # Start keepalive as background task
    keepalive_task = asyncio.create_task(
        send_keepalive(websocket, client_id)
    )
    
    try:
        # Handle client messages...
        while True:
            data = await websocket.receive_text()
            
            if data == 'pong':
                logger.debug(f"Received pong from client {client_id}")
            # Handle other messages...
            
    finally:
        # Clean up on disconnect
        keepalive_task.cancel()
        await broadcaster.disconnect(websocket)
```

### Client-Side Implementation

Browser clients must respond to pings:

```javascript
const ws = new WebSocket('ws://localhost:3002/ws/events');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'ping') {
    // Respond to keepalive ping
    ws.send(JSON.stringify({ type: 'pong' }));
  } else {
    // Handle state machine events
    handleStateEvent(data);
  }
};
```

### Timeout Detection

Clients typically timeout after missing 2-3 pings:

- **Ping interval**: 10 seconds
- **Typical client timeout**: 20-30 seconds
- **Server detection**: Connection error on next send

If a client stops responding to pings, the WebSocket will eventually close, triggering cleanup in the `finally` block.

---

## Connection Lifecycle

### 1. Client Connection

```
Client                                Server
  │                                     │
  │  WebSocket handshake                │
  │────────────────────────────────────>│
  │                                     │
  │  101 Switching Protocols            │
  │<────────────────────────────────────│
  │                                     │
  │  Initial state snapshot             │
  │<────────────────────────────────────│
  │  {type: "initial", machines: [...]} │
  │                                     │
  │  Keepalive task started             │
  │                                     │
```

### 2. Event Streaming

```
State Machine              Server                   Client
     │                       │                        │
     │  Unix socket event    │                        │
     │──────────────────────>│                        │
     │                       │  WebSocket broadcast   │
     │                       │───────────────────────>│
     │                       │                        │
```

### 3. Keepalive Loop

```
Server                                  Client
  │                                       │
  │  {"type": "ping"}                     │
  │──────────────────────────────────────>│
  │                                       │
  │  {"type": "pong"}                     │
  │<──────────────────────────────────────│
  │                                       │
  │  (10 second wait)                     │
  │                                       │
  │  {"type": "ping"}                     │
  │──────────────────────────────────────>│
  │                                       │
```

### 4. Disconnection

```
Client                                Server
  │                                     │
  │  Close connection                   │
  │────────────────────────────────────>│
  │                                     │
  │                                     │  Cancel keepalive task
  │                                     │  Remove from broadcaster
  │                                     │
  │  Close acknowledgment               │
  │<────────────────────────────────────│
  │                                     │
```

---

## Message Types

### Server → Client Messages

#### Initial State
Sent immediately upon connection:
```json
{
  "type": "initial",
  "machines": [
    {
      "id": "worker-123",
      "current_state": "idle",
      "last_activity": 1729845678.123
    }
  ],
  "timestamp": 1729845678.123
}
```

#### State Change Event
Broadcasted when state machines change state:
```json
{
  "type": "state_change",
  "machine_id": "worker-123",
  "state": "processing",
  "previous_state": "idle",
  "timestamp": 1729845678.123,
  "data": {
    "job_id": "task-456"
  }
}
```

#### Ping
Keepalive heartbeat:
```json
{
  "type": "ping",
  "timestamp": 1729845678.123
}
```

### Client → Server Messages

#### Pong
Response to ping:
```json
{
  "type": "pong"
}
```

#### Refresh Request
Request fresh state snapshot:
```json
{
  "type": "refresh"
}
```

---

## Error Handling

### Unix Socket Errors
- **Socket not found**: State machine logs debug message, continues execution
- **Permission denied**: Check socket file permissions
- **Connection refused**: WebSocket server not running (expected, not fatal)

### WebSocket Errors
- **Client timeout**: Connection closed, removed from broadcaster
- **Send failure**: Client marked as dead, removed from broadcaster
- **JSON serialization failure**: Event dropped, error logged

### Event Loop Blocking Prevention

The server uses multiple strategies to prevent blocking:

1. **Pre-serialization**: JSON serialization done before `await`
2. **Timeouts**: All network operations have 2-second timeout
3. **Watchdog thread**: Detects event loop hangs >15 seconds
4. **Emergency logging**: Fallback file logging if main logger blocks
5. **Server heartbeat**: Logs every 5 seconds to prove event loop is running

---

## Performance Characteristics

### Throughput
- **Unix socket**: ~100,000 events/sec (limited by serialization)
- **WebSocket broadcast**: ~1,000 events/sec per client (network limited)
- **Typical load**: 10-100 events/sec across all machines

### Latency
- **Unix socket → Server**: <1ms (local IPC)
- **Server → WebSocket client**: 2-5ms (localhost network)
- **End-to-end**: 3-6ms (state change to browser update)

### Scalability
- **State machines**: Unlimited (fire-and-forget to Unix socket)
- **WebSocket clients**: Tested up to 50 concurrent (CPU bound on broadcast)
- **Broadcast bottleneck**: JSON serialization and network I/O

### Memory Usage
- **Base server**: ~50 MB
- **Per client**: ~1 MB (WebSocket overhead + event queue)
- **Event buffer**: Unbounded (potential memory leak if clients slow)

---

## Monitoring & Debugging

### Server Logs
Location: `logs/websocket-server.log`

Key log patterns:
```
🚀 WebSocket Server v1.0.26 Starting Up
✅ ALL websocket.send_json() calls replaced with send_text()
📋 Client 12345: Fetching initial state...
✅ Client 12345: Initial state sent successfully
🏓 Client 12345: Sending keepalive ping
📨 Received event from Unix socket: {"type": "state_change", ...}
🔊 Broadcasting event to 3 clients (2.39ms)
💓 Server heartbeat - 3 clients, event loop healthy
```

### Watchdog Alerts
If the event loop hangs >15 seconds:
```
🚨 SERVER HANG DETECTED! Last activity 15.4 seconds ago
📍 Possible freeze point: send_keepalive
💾 Emergency stack trace written to logs/hang-emergency.log
```

### Client-Side Debugging
```javascript
ws.onclose = (event) => {
  console.log('WebSocket closed:', event.code, event.reason);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

Common error codes:
- **1000**: Normal closure
- **1006**: Abnormal closure (no close frame)
- **1011**: Internal server error

---

## Configuration

### Server Configuration
```python
# WebSocket server
HOST = "0.0.0.0"
PORT = 3002
CORS_ORIGINS = ["*"]  # Allow all origins for development

# Unix socket
SOCKET_PATH = "/tmp/statemachine-events.sock"
SOCKET_BUFFER = 4096  # bytes per message

# Keepalive
PING_INTERVAL = 10  # seconds
SEND_TIMEOUT = 2.0  # seconds

# Watchdog
HANG_THRESHOLD = 15  # seconds
```

### Client Configuration
```javascript
const WS_URL = 'ws://localhost:3002/ws/events';
const RECONNECT_DELAY = 5000;  // ms
const PING_TIMEOUT = 30000;    // ms
```

---

## Best Practices

### State Machines
1. **Fire and forget**: Never wait for event acknowledgment
2. **Fail silently**: Don't crash if WebSocket server is down
3. **Throttle events**: Avoid sending >100 events/sec per machine
4. **Include context**: Send enough data for UI to render state

### WebSocket Server
1. **Pre-serialize JSON**: Never call `json.dumps()` inside `await`
2. **Use timeouts**: Protect all network operations
3. **Clean up dead connections**: Remove failed clients from broadcaster
4. **Monitor event loop**: Use watchdog and heartbeat tasks

### Browser Clients
1. **Handle reconnection**: Implement exponential backoff
2. **Respond to pings**: Send pong to keep connection alive
3. **Handle initial state**: Don't assume events arrive in order
4. **Throttle updates**: Debounce UI updates to avoid render thrashing

---

## Troubleshooting

### "WebSocket connection closed immediately"
**Cause**: Server not running or CORS issue  
**Fix**: Check server logs, verify CORS settings

### "Keepalive ping timeout; no close frame received"
**Cause**: Event loop blocked, server frozen  
**Fix**: Check for synchronous operations in async code, review watchdog logs

### "Unix socket permission denied"
**Cause**: Socket file has wrong permissions  
**Fix**: `chmod 666 /tmp/statemachine-events.sock`

### "Events not reaching browser"
**Cause**: State machine using wrong socket path, or broadcaster failed  
**Fix**: Check `SOCKET_PATH` matches on both sides, review broadcast logs

### "Server using 100% CPU"
**Cause**: Tight loop without `await` yield points  
**Fix**: Add `await asyncio.sleep(0)` in loops, use proper async patterns

### "Memory leak - server RAM growing"
**Cause**: Dead WebSocket connections not cleaned up  
**Fix**: Ensure `broadcaster.disconnect()` called in `finally` blocks

---

## Version History

- **v1.0.26**: Fixed ALL `websocket.send_json()` blocking calls (initial, ping, pong, refresh)
- **v1.0.25**: Fixed `broadcast()` blocking by pre-serializing JSON
- **v1.0.21-24**: Added watchdog, heartbeat, emergency logging, freeze detection
- **v1.0.20**: Added timeout to WebSocket sends (incomplete fix)
- **v1.0.18**: Original implementation with blocking issues

---

## References

- [WebSocket Protocol (RFC 6455)](https://datatracker.ietf.org/doc/html/rfc6455)
- [Unix Domain Sockets](https://en.wikipedia.org/wiki/Unix_domain_socket)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [Starlette WebSocket](https://www.starlette.io/websockets/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
