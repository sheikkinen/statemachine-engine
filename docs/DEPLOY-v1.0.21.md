# 🐕 Server Hang Detection System - v1.0.21

## What Was Implemented

A comprehensive **3-layer monitoring system** to detect, diagnose, and troubleshoot server hangs:

### Layer 1: Watchdog Thread 🐕
- **Separate OS thread** monitoring event loop health
- Dumps **complete stack traces** if no heartbeat for >15 seconds
- Shows **exact line of code** where server is frozen
- Cannot be blocked by Python event loop freeze

### Layer 2: Server Heartbeat 💓
- Logs health every **5 seconds**: connections, tasks, last event time
- If heartbeat stops → event loop is frozen
- If heartbeat continues but events stop → specific operation is frozen

### Layer 3: Performance Monitoring ⏱️
- Times all critical operations
- Warns if operations exceed thresholds:
  - Broadcast: >50ms
  - Database queries: >200ms
- Logs complete event processing pipeline timing

## What You'll See

### Normal Operation
```log
💓 Server heartbeat #1 | connections=2 | tasks=5 | last_event=0.1s ago
📥 Unix socket: Event #35 parsed in 1.23ms
✅ Broadcast complete for event #35 in 2.45ms
💓 Server heartbeat #2 | connections=2 | tasks=5 | last_event=0.2s ago
```

### During Server Hang
```log
💓 Server heartbeat #10 | connections=2 | tasks=5 | last_event=0.1s ago
⏱️  START: broadcast_event
[15 seconds pass with NO logs - event loop frozen]
🚨 SERVER HANG DETECTED: No heartbeat for 16.2s
🚨 DUMPING ALL THREAD STACK TRACES:
================================================================================
Thread 12345 (MainThread):
  File "websocket_server.py", line 245, in unix_socket_listener
    await broadcaster.broadcast(event)
  File "websocket_server.py", line 82, in broadcast
    await asyncio.wait_for(ws.send_json(event), timeout=2.0)
  File "websockets/protocol.py", line 456, in send_json
    await self.send(data)
================================================================================

⚠️  SLOW OPERATION: broadcast_event took 35234.56ms
💓 Server heartbeat #17 | connections=1 | tasks=5 | last_event=40.1s ago
```

**This tells you**:
1. **WHERE**: Exact file and line number where frozen
2. **WHAT**: `broadcast_event` operation (WebSocket send)
3. **HOW LONG**: 35.2 seconds
4. **WHEN**: Timestamp shows when it started/ended

## How to Use

### Deploy v1.0.21
```bash
# From statemachine-engine directory
git pull
pip install -e .

# Restart WebSocket server
pkill -f websocket_server
statemachine-engine websocket
```

### Monitor for Hangs
```bash
# Real-time log monitoring
tail -f logs/websocket-server.log
```

### When Hang Occurs

**Step 1**: Look for heartbeat stopping
```
💓 Server heartbeat #10 | ...
[NO MORE HEARTBEATS FOR 15+ SECONDS]
```

**Step 2**: Find watchdog alert
```
🚨 SERVER HANG DETECTED: No heartbeat for 16.2s
🚨 DUMPING ALL THREAD STACK TRACES:
```

**Step 3**: Read stack trace
```
File "websocket_server.py", line 245
    await broadcaster.broadcast(event)
```
→ Frozen in `broadcast()` function at line 245

**Step 4**: Check timing
```
⚠️  SLOW OPERATION: broadcast_event took 35234.56ms
```
→ Broadcast took 35 seconds (should be <50ms)

**Step 5**: Determine root cause
- **If blocking on `ws.send_json()`**: Slow/dead WebSocket client
- **If blocking on `json.loads()`**: Huge JSON payload
- **If blocking on database**: Slow query or lock
- **If blocking on `socket.recv()`**: Unix socket buffer issue

## Testing the System

Run the test script to verify watchdog works:

```bash
cd /Users/sheikki/Documents/src/statemachine-engine
python tests/test_hang_detection.py
```

**Expected output**:
- TEST 1: No watchdog (5s < 15s timeout) ✅
- TEST 2: Watchdog detects 20s hang ✅
- TEST 3: Recovery after hang ✅

## Key Improvements from Previous Versions

| Version | Issue | Fix |
|---------|-------|-----|
| v1.0.18 | Keepalive not sending | Separated into background task |
| v1.0.19 | Can't see what's happening | Added comprehensive logging |
| v1.0.20 | 40s broadcast block | Added 2s timeout to `ws.send_json()` |
| **v1.0.21** | **Don't know WHERE/WHY hangs** | **Watchdog + stack traces + timing** |

## Configuration

All timeouts and intervals can be adjusted:

```python
# In websocket_server.py

# Watchdog hang detection
watchdog = WatchdogThread(perf_monitor, timeout=15)  # 15 seconds

# Server heartbeat
await asyncio.sleep(5)  # Log every 5 seconds

# Performance warnings
@log_timing("broadcast_event", warn_threshold_ms=50)  # Warn if >50ms
@log_timing("get_initial_state", warn_threshold_ms=200)  # Warn if >200ms

# WebSocket keepalive
ping_interval = 10  # Send ping every 10 seconds

# Broadcast timeout
await asyncio.wait_for(ws.send_json(event), timeout=2.0)  # 2 second max
```

## Next Steps

### 1. Deploy and Monitor
```bash
# Deploy v1.0.21
pip install -e .

# Restart server
statemachine-engine websocket

# Watch logs
tail -f logs/websocket-server.log | grep -E "(💓|🚨|⚠️)"
```

### 2. Wait for Hang to Occur
- System will automatically detect and log
- No manual intervention needed
- Complete diagnostic data in logs

### 3. Analyze Results
- Check stack traces for exact location
- Check timing for duration
- Check heartbeat for event loop health

### 4. Implement Fix
Based on stack trace:
- WebSocket blocking → increase timeout or improve client
- JSON parsing blocking → optimize payload size
- Database blocking → optimize query or add index
- Socket blocking → increase buffer or add timeout

## Files Changed

- ✅ `src/statemachine_engine/monitoring/websocket_server.py` - Monitoring system
- ✅ `docs/hang-detection-plan.md` - Strategy document
- ✅ `docs/hang-detection-implementation.md` - Technical details
- ✅ `docs/DEPLOY-v1.0.21.md` - This deployment guide
- ✅ `tests/test_hang_detection.py` - Test script
- ✅ `CHANGELOG.md` - Version history
- ✅ `pyproject.toml` - Version bump

## Ready to Deploy

Version 1.0.21 is ready for:
1. **Testing**: Run `python tests/test_hang_detection.py`
2. **Commit**: `git add -A && git commit -m "v1.0.21: Add comprehensive hang detection"`
3. **Release**: `git push && git tag v1.0.21 && git push --tags`
4. **Deploy**: `pip install -e .` in production

The next time the server hangs, you'll get **complete diagnostic data** showing exactly where and why it froze.
