# Server Hang Detection - Implementation Summary

## Overview
Implemented comprehensive hang detection and performance monitoring system to troubleshoot server freezes.

## Problem
WebSocket server freezes at unpredictable times, blocking all event delivery and keepalive pings for 30-40 seconds.

## Solution: Multi-Layer Monitoring

### 1. Watchdog Thread (Primary Detection)
**Location**: `websocket_server.py` - `WatchdogThread` class

```python
class WatchdogThread(threading.Thread):
    """Watchdog that dumps stack traces if server hangs"""
    timeout = 15  # seconds
```

**How it works**:
- Runs in separate OS thread (not affected by asyncio event loop freeze)
- Monitors `perf_monitor.last_heartbeat` timestamp
- If no heartbeat for >15 seconds, dumps **complete stack traces** of all threads
- Shows exact line of code where server is frozen

**Output on hang**:
```
🚨 SERVER HANG DETECTED: No heartbeat for 16.2s
🚨 DUMPING ALL THREAD STACK TRACES:
================================================================================
Thread 12345 (MainThread):
  File "/path/to/websocket_server.py", line 82, in broadcast
    await ws.send_json(event)
  File "/path/to/websockets/protocol.py", line 456, in send_json
    await self.send(data)
================================================================================
```

### 2. Server Heartbeat (Health Check)
**Location**: `websocket_server.py` - `server_heartbeat()` async task

```python
async def server_heartbeat():
    """Logs server health every 5 seconds"""
```

**What it logs**:
```
💓 Server heartbeat #123 | connections=2 | tasks=5 | last_event=3.2s ago
```

**Detection method**:
- If heartbeat logs STOP appearing → event loop is frozen
- If heartbeat continues but event processing stops → specific operation is frozen
- High task count warning if >10 active tasks (potential leak)

### 3. Performance Monitor (Operation Timing)
**Location**: `websocket_server.py` - `PerformanceMonitor` class

```python
class PerformanceMonitor:
    """Monitor for detecting slow operations"""
```

**Tracks**:
- Every critical operation wrapped with `@log_timing()` decorator
- Warns if operation exceeds threshold (50ms for broadcast, 200ms for DB)
- Updates watchdog heartbeat on successful completion

**Wrapped operations**:
1. `broadcast_event` - warns if >50ms
2. `get_initial_state` - warns if >200ms  
3. Unix socket receive - logs all stages with timing

### 4. Pipeline Stage Timing
**Location**: `unix_socket_listener()` function

**Tracks event through stages**:
```
⏱️  START: unix socket receive
🔌 Unix socket: Received 1234 bytes in 0.52ms
📥 Event #35 parsed in 1.23ms
📡 Broadcasting to 2 clients
✅ Broadcast complete in 2.45ms
```

**Detection method**:
- If parse takes >100ms → large JSON payload issue
- If broadcast takes >50ms → slow client or network issue
- If receive takes >100ms → socket buffer or OS issue

## Usage

### Normal Operation
Logs show regular heartbeats and quick operations:
```
💓 Server heartbeat #1 | connections=2 | tasks=5 | last_event=0.1s ago
⏱️  END: broadcast_event (1.23ms)
💓 Server heartbeat #2 | connections=2 | tasks=5 | last_event=0.2s ago
```

### During Hang
Watchdog detects freeze and dumps stack:
```
💓 Server heartbeat #1 | connections=2 | tasks=5 | last_event=0.1s ago
⏱️  START: broadcast_event
⚠️  SLOW: broadcast_event took 35000.00ms
🚨 SERVER HANG DETECTED - DUMPING STACK TRACES
[Stack traces showing exact blocking location]
💓 Server heartbeat #8 | connections=2 | tasks=5 | last_event=40.1s ago
```

### After Hang
Performance monitor shows slow operation:
```
⚠️  SLOW OPERATION: broadcast_event took 35234.56ms
```

## Key Configuration

| Component | Interval/Timeout | Purpose |
|-----------|-----------------|---------|
| Watchdog | 15s timeout | Hang detection, stack dump |
| Heartbeat | 5s interval | Health check, alive signal |
| Broadcast | 50ms warn | Slow client detection |
| DB Query | 200ms warn | Slow database query |
| Keepalive | 10s interval | WebSocket ping (reduced from 20s) |

## What Gets Logged

### On Every Event
```
📥 Unix socket: Event #35 (dimensions_verified) from face_processor - parsed in 1.23ms
📡 Broadcasting event #35 to 2 clients
📤 Broadcasting to client 4531964240: dimensions_verified event
📦 Event content: {...full JSON...}
✅ Sent to client 4531964240
✅ Broadcast complete for event #35 in 2.45ms
```

### On Hang (Automatically)
```
🚨 SERVER HANG DETECTED: No heartbeat for 16.2s
🚨 DUMPING ALL THREAD STACK TRACES:
[Complete stack trace of all threads]
```

### On Slow Operation
```
⚠️  SLOW OPERATION: broadcast_event took 234.56ms
⚠️  High task count: 15 active tasks
```

## Troubleshooting Workflow

### Step 1: Reproduce Issue
- Deploy v1.0.21
- Monitor logs in real-time: `tail -f logs/websocket-server.log`

### Step 2: Detect Hang
- Heartbeat logs stop appearing → event loop frozen
- Watchdog dumps stack traces → exact blocking location

### Step 3: Analyze Stack Trace
```
File "/path/to/websocket_server.py", line 82, in broadcast
    await ws.send_json(event)
```
→ Blocking on WebSocket send

### Step 4: Check Timing Logs
```
⚠️  SLOW OPERATION: broadcast_event took 35000.00ms
```
→ Broadcast took 35 seconds (should be <50ms)

### Step 5: Root Cause
- Stack trace shows WHERE it's stuck
- Timing logs show WHAT is slow
- Heartbeat shows IF event loop is alive

## Expected Outcomes

When server hangs again:
1. **Watchdog will log exact blocking location** (stack trace)
2. **Heartbeat will stop** (proves event loop frozen)
3. **Timing logs will show slow operation** (quantifies hang duration)
4. **No guessing needed** - exact file, line number, and function

## Future Enhancements (Optional)

If needed, can add:
- Circuit breaker (auto-restart on freeze >30s)
- Debug mode flag (even more verbose logging)
- Task state monitoring (track all asyncio task states)
- Connection pool monitoring (track WebSocket send queues)

## Files Modified

- `src/statemachine_engine/monitoring/websocket_server.py` - All monitoring code
- `docs/hang-detection-plan.md` - Troubleshooting strategy
- `docs/hang-detection-implementation.md` - This document
- `CHANGELOG.md` - v1.0.21 changes
- `pyproject.toml` - Version bump to 1.0.21
