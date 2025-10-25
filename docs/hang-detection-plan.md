# Server Hang Detection & Troubleshooting Plan

## Problem Statement
The WebSocket server freezes/hangs at unpredictable times, blocking all event delivery and keepalive pings. The hang appears to last 30-40 seconds before recovering.

## Root Cause Hypotheses

### 1. **Blocking I/O Operation**
- JSON serialization of large payloads
- Socket recv/send blocking despite async
- File I/O in logging
- Database operations

### 2. **Event Loop Starvation**
- CPU-intensive synchronous operation
- Missing `await` causing sync execution
- Event loop blocked by long-running task

### 3. **Deadlock/Race Condition**
- Multiple tasks competing for shared resource
- Lock contention
- Circular wait on async operations

### 4. **Memory/Resource Exhaustion**
- Memory allocation causing GC pause
- Too many queued events
- Socket buffer overflow

## Instrumentation Strategy

### Phase 1: Non-Invasive Monitoring (Immediate)
Add logging that won't affect performance but provides visibility.

**1.1 Server Heartbeat**
- Background task that logs "💓 Server alive" every 5 seconds
- If this stops, we know event loop is frozen
- Logs timestamp + active connection count

**1.2 Operation Timing Wrapper**
```python
import time
import functools

def log_timing(operation_name, warn_threshold_ms=100):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            logger.debug(f"⏱️  START: {operation_name}")
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                if duration_ms > warn_threshold_ms:
                    logger.warning(f"⚠️  SLOW: {operation_name} took {duration_ms:.2f}ms")
                else:
                    logger.debug(f"⏱️  END: {operation_name} ({duration_ms:.2f}ms)")
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                logger.error(f"❌ FAILED: {operation_name} after {duration_ms:.2f}ms: {e}")
                raise
        return wrapper
    return decorator
```

**1.3 Event Processing Pipeline Tracking**
```python
# Track event through all stages
event_stages = {
    'received': time.time(),
    'parsed': None,
    'queued': None,
    'broadcast_started': None,
    'broadcast_completed': None
}
```

### Phase 2: Active Monitoring (After initial data)
Add monitoring that may have slight performance impact.

**2.1 Async Task Monitor**
```python
async def monitor_tasks():
    """Log all asyncio tasks every 10 seconds"""
    while True:
        await asyncio.sleep(10)
        tasks = asyncio.all_tasks()
        logger.info(f"📊 Active tasks: {len(tasks)}")
        for task in tasks:
            logger.debug(f"  - {task.get_name()}: {task._state}")
```

**2.2 Connection State Monitor**
```python
async def monitor_connections():
    """Track WebSocket connection health"""
    while True:
        await asyncio.sleep(5)
        for client_id, ws in active_connections.items():
            # Log connection state, send queue depth, etc.
            logger.info(f"🔌 Client {client_id}: state={ws.client_state}")
```

**2.3 Socket Buffer Monitor**
```python
# Check Unix socket receive buffer
import fcntl
bytes_available = fcntl.ioctl(sock.fileno(), termios.FIONREAD)
if bytes_available > 10000:
    logger.warning(f"⚠️  Socket buffer has {bytes_available} bytes queued")
```

### Phase 3: Hang Detection (Nuclear option)
Aggressive monitoring for production debugging.

**3.1 Watchdog Thread**
```python
import threading
import traceback
import sys

class Watchdog(threading.Thread):
    def __init__(self, timeout=10):
        super().__init__(daemon=True)
        self.timeout = timeout
        self.last_heartbeat = time.time()
        self.running = True
    
    def heartbeat(self):
        self.last_heartbeat = time.time()
    
    def run(self):
        while self.running:
            time.sleep(1)
            if time.time() - self.last_heartbeat > self.timeout:
                logger.critical("🚨 SERVER HANG DETECTED - DUMPING STACK TRACES")
                for thread_id, frame in sys._current_frames().items():
                    logger.critical(f"Thread {thread_id}:")
                    logger.critical(''.join(traceback.format_stack(frame)))
                self.last_heartbeat = time.time()  # Reset to avoid spam
```

**3.2 Circuit Breaker**
```python
async def circuit_breaker():
    """Kill server if frozen too long"""
    last_event_time = time.time()
    while True:
        await asyncio.sleep(1)
        if time.time() - last_event_time > 30:
            logger.critical("🚨 CIRCUIT BREAKER: Server frozen >30s, forcing shutdown")
            os._exit(1)  # Hard exit
```

## Implementation Plan

### Step 1: Add Heartbeat (5 minutes)
- Add `server_heartbeat()` task to websocket_server.py
- Logs every 5 seconds with timestamp
- If this stops, event loop is frozen

### Step 2: Wrap Key Operations (15 minutes)
- Wrap `unix_socket_listener()` receive loop
- Wrap `EventBroadcaster.broadcast()`
- Wrap `ws.send_json()` calls
- Wrap JSON serialization

### Step 3: Add Pipeline Tracking (10 minutes)
- Log timestamps at: receive, parse, queue, broadcast_start, broadcast_end
- Calculate deltas to find bottleneck stage

### Step 4: Add Watchdog (10 minutes)
- Create watchdog thread
- Call `watchdog.heartbeat()` in main event loop
- Dumps stack traces if no heartbeat for 10 seconds

### Step 5: Deploy & Monitor (Ongoing)
- Deploy instrumented version
- Run under production load
- Analyze logs when hang occurs
- Stack traces will show exact blocking point

## Expected Outputs

### Normal Operation
```
💓 Server alive | ts=1234.567 | connections=2 | tasks=5
⏱️  START: broadcast_event
⏱️  END: broadcast_event (1.23ms)
💓 Server alive | ts=1239.567 | connections=2 | tasks=5
```

### During Hang
```
💓 Server alive | ts=1234.567 | connections=2 | tasks=5
⏱️  START: broadcast_event
⚠️  SLOW: broadcast_event took 35000.00ms
🚨 SERVER HANG DETECTED - DUMPING STACK TRACES
Thread 12345:
  File "/path/to/websocket_server.py", line 82, in broadcast
    await ws.send_json(event)
  File "/path/to/websockets/protocol.py", line 456, in send_json
    await self.send(data)
💓 Server alive | ts=1269.567 | connections=2 | tasks=5
```

## Success Criteria
1. Can reproduce hang in logs with exact timestamp
2. Stack trace shows exact line of code where hung
3. Timing data shows which operation is blocking
4. Can correlate hang with specific event or client

## Next Steps After Data Collection
- If blocking on `ws.send_json()`: Already fixed with timeout (verify timeout value)
- If blocking on JSON serialization: Add streaming or chunking
- If blocking on socket recv: Add timeout to socket operations
- If blocking on logging: Switch to async logging or buffer
- If GC pause: Tune Python GC or reduce object creation
