# WebSocket Communication Failure Analysis - October 24, 2025

## Root Cause: Slow Client Blocking Broadcast

**Issue**: WebSocket client timeout with error: "keepalive ping timeout; no close frame received"

**Duration**: System appeared to hang for ~40 seconds (23:53:17 to 23:53:56)

## Unix Socket Emissions Timeline

### Event #1: State Change - Faces Cropped
**Timestamp**: 1761339196.6836941 (23:53:16.683)
```json
{
  "machine_name": "face_processor",
  "event_type": "state_change",
  "payload": {
    "from_state": "cropping_faces",
    "to_state": "verifying_portraits",
    "event_trigger": "faces_cropped",
    "timestamp": 1761339196.6836941
  }
}
```
- Emitted: 23:53:16.684
- Size: 211 bytes
- ✅ Successfully emitted

### Event #2: State Change - Portraits Verified
**Timestamp**: 1761339196.965557 (23:53:16.965)
```json
{
  "machine_name": "face_processor",
  "event_type": "state_change",
  "payload": {
    "from_state": "verifying_portraits",
    "to_state": "verifying_dimensions",
    "event_trigger": "portraits_verified",
    "timestamp": 1761339196.965557
  }
}
```
- Emitted: 23:53:16.965
- Size: 221 bytes
- ✅ Successfully emitted

### Event #3: State Change - Dimensions Verified ⚠️ CRITICAL EVENT
**Timestamp**: 1761339197.342266 (23:53:17.342)
```json
{
  "machine_name": "face_processor",
  "event_type": "state_change",
  "payload": {
    "from_state": "verifying_dimensions",
    "to_state": "detecting_faces",
    "event_trigger": "dimensions_verified",
    "timestamp": 1761339197.342266
  }
}
```
- Emitted: 23:53:17.343
- Size: 218 bytes
- ✅ Successfully emitted from engine
- ❌ **BROADCAST BLOCKED FOR 39.6 SECONDS**

### Event #4: State Change - Faces Detected
**Timestamp**: 1761339200.473602 (23:53:20.473)
```json
{
  "machine_name": "face_processor",
  "event_type": "state_change",
  "payload": {
    "from_state": "detecting_faces",
    "to_state": "running_inpainting",
    "event_trigger": "faces_detected",
    "timestamp": 1761339200.473602
  }
}
```
- Emitted: 23:53:20.473
- Size: 211 bytes
- ✅ Successfully emitted from engine
- ⏳ Queued behind blocked broadcast

## WebSocket Server Broadcast Timeline

### Event #34 (portraits_verified)
- **Received**: 23:53:16.966
- **Client 4502217664**: Sent at 23:53:16.966 ✅
- **Client 4502220496**: Sent at 23:53:16.967 ✅

### Event #35 (activity_log - "Verifying dimensions")
- **Received**: 23:53:17.182
- **Client 4502217664**: Sent at 23:53:17.183 ✅
- **Client 4502220496**: Sent at 23:53:17.183 ✅

### Event #36 (dimensions_verified) - THE BLOCKING EVENT
- **Received**: 23:53:17.343
- **Broadcast started to client 4502217664**: 23:53:17.344
- **⚠️  BLOCKED FOR 39.603 SECONDS**
- **Broadcast completed to client 4502217664**: 23:53:56.947 ❌
- **Broadcast started to client 4502220496**: 23:53:56.948
- **Broadcast completed to client 4502220496**: 23:53:56.948 ✅

**Analysis**: The `await ws.send_json(event)` call to client 4502217664 blocked for nearly 40 seconds. This prevented:
- Further broadcasts from being processed
- Keepalive pings from being sent
- The event loop from processing other tasks

### Event #37 (activity_log - "Generating face masks")
- **Received**: 23:53:56.949
- **Client 4502217664**: Sent at 23:53:56.950 ✅
- **Client 4502220496**: ❌ FAILED - Client already disconnected

### Event #38 (faces_detected)
- **Received**: 23:53:56.953
- **Client 4502217664**: Sent at 23:53:56.954 ✅

### Event #39 (activity_log - "Starting inpainting")
- **Received**: 23:53:56.955
- **Client 4502217664**: Sent at 23:53:56.956 ✅

## Client Disconnection Sequence

### Client 4502220496 (First to disconnect)
- **23:53:56.958**: Keepalive task tried to send ping
- **Error**: "Cannot call 'send' once a close message has been sent"
- **Reason**: Client timed out waiting for server keepalive pings during the 40-second block

### Client 4502217664 (Second to disconnect)
- **23:53:56.958**: Client sent ping (client-initiated)
- **23:53:56.966**: Server tried to send keepalive ping
- **23:53:56.967**: Keepalive task cancelled
- **23:53:56.968**: Client disconnected normally

## Root Cause Analysis

### The Problem
```python
# Old code - NO TIMEOUT
for ws in self.connections:
    await ws.send_json(event)  # Can block indefinitely!
```

When a WebSocket client:
1. Has a full receive buffer
2. Is processing slowly
3. Has network congestion
4. Is debugging/paused

The `send_json()` call blocks until the client can receive, which can be **indefinite**.

### Timeline of Failure
1. **23:53:17.344** - Started sending event #36 to client 4502217664
2. **23:53:17 to 23:53:56** - Blocked for 39.6 seconds
3. During block:
   - No keepalive pings sent to ANY client
   - Event queue backing up (events #37, #38, #39)
   - Client 4502220496 timeout (expected ping every 20s, got none for 40s)
4. **23:53:56.947** - Send finally completed
5. **23:53:56.948** - Client 4502220496 already disconnected
6. **23:53:56.968** - Client 4502217664 also disconnected

## The Fix

```python
# New code - WITH TIMEOUT
for ws in self.connections:
    try:
        await asyncio.wait_for(ws.send_json(event), timeout=2.0)
    except asyncio.TimeoutError:
        logger.warning(f"Client {id(ws)}: Send timed out after 2s, marking as dead")
        dead_connections.add(ws)
```

### Benefits
1. **No blocking**: Slow clients can't block broadcasts to other clients
2. **Timely keepalives**: Ping tasks run on schedule
3. **Fast recovery**: Dead/slow clients removed within 2 seconds
4. **System resilience**: One slow client doesn't affect the entire system

## Lessons Learned

1. **Always timeout network I/O** - Even "async" operations can block
2. **Monitor critical paths** - The comprehensive logging revealed the exact block
3. **Test with slow clients** - Need integration tests simulating slow receivers
4. **Separate concerns** - Keepalive should be independent of broadcast queue

## Metrics

- **Block Duration**: 39.603 seconds
- **Events Queued**: 3 (events #37, #38, #39)
- **Clients Lost**: 2 (both disconnected due to ping timeout)
- **System Downtime**: ~40 seconds (from user perspective)
- **Messages Lost**: 0 (all queued events processed after unblock)

## Prevention

1. ✅ Added 2-second timeout to `ws.send_json()`
2. ✅ Keepalive runs in separate task (already implemented)
3. ✅ Comprehensive logging shows exact blocking points
4. 🔜 TODO: Add monitoring for slow client detection
5. 🔜 TODO: Add metrics for broadcast latency per client
6. 🔜 TODO: Integration test for slow client scenarios
