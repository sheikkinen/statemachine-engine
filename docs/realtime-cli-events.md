# Real-time CLI Event Delivery (v0.0.20)

## Overview

The `send-event` CLI command now delivers events instantly to the Web UI via Unix socket, eliminating the need for page refresh or polling to see activity log messages.

## What Changed

### Before (v0.0.19)
```
CLI send-event → Database → (polling required) → UI
```
- Events written to database only
- UI required page refresh or polling to see updates
- Delay between CLI action and UI display

### After (v0.0.20)
```
CLI send-event → Database + Unix Socket → WebSocket → UI (instant)
```
- Events written to both database AND Unix socket
- UI receives instant updates via WebSocket
- Zero-latency display in Activity Log tab

## How It Works

### Event Routing

The `send-event` command now sends to multiple destinations:

1. **Database** (`machine_events` table) - Persistent audit trail
2. **WebSocket Socket** (`/tmp/statemachine-events.sock`) - Real-time UI updates
3. **Machine Control Socket** (`/tmp/statemachine-control-{machine}.sock`) - Direct machine communication (if applicable)

### Socket Routing Logic

```python
# UI target → WebSocket socket only
--target ui → /tmp/statemachine-events.sock

# Machine target → Both WebSocket + control socket
--target worker1 → /tmp/statemachine-events.sock + /tmp/statemachine-control-worker1.sock
```

## Usage Examples

### Send Activity Log to UI

```bash
# Basic usage
statemachine-db send-event \
  --target ui \
  --type activity_log \
  --payload '{"message": "Task completed", "level": "SUCCESS"}'

# With custom source attribution
statemachine-db send-event \
  --target ui \
  --type activity_log \
  --source my_custom_tool \
  --payload '{"message": "Processing file.txt", "level": "INFO"}'
```

### Send to State Machine

```bash
# Event goes to machine control socket + WebSocket UI
statemachine-db send-event \
  --target worker1 \
  --type custom_event \
  --job-id job123 \
  --payload '{"data": "value"}'
```

## New Parameters

### `--source` (Optional)

Specifies the source machine name for UI attribution.

**Default:** `"cli"`

**Example:**
```bash
--source my_tool  # Shows as "my_tool" in UI instead of "cli"
```

## Event Format

### WebSocket Socket Message

```json
{
  "machine_name": "cli",          // From --source, defaults to "cli"
  "event_type": "activity_log",   // From --type
  "payload": {                     // From --payload (parsed JSON)
    "message": "Task completed",
    "level": "SUCCESS"
  }
}
```

### Machine Control Socket Message

```json
{
  "type": "custom_event",          // From --type
  "payload": {                     // From --payload (parsed JSON)
    "data": "value"
  },
  "job_id": "job123"               // From --job-id (optional)
}
```

## Requirements

### For Real-time UI Updates

- WebSocket server must be running (`statemachine-ui`)
- Unix socket `/tmp/statemachine-events.sock` must exist

### Graceful Fallback

If WebSocket server is unavailable:
- Event still written to database ✅
- No real-time UI update ⚠️
- Command succeeds (exit code 0) ✅
- Warning message displayed

## Testing

### Automated Tests

8 new tests in `tests/database/test_cli_send_event_realtime.py`:

```bash
pytest tests/database/test_cli_send_event_realtime.py -v
```

**Test Coverage:**
- WebSocket socket delivery
- Dual-socket routing (WebSocket + control)
- Graceful error handling
- JSON payload parsing
- Source attribution defaults
- Socket unavailability handling

### Manual Testing

Run the manual test script:

```bash
python tests/manual_test_realtime_delivery.py
```

**Verification Steps:**
1. Start WebSocket server: `statemachine-ui`
2. Open Web UI in browser
3. Run manual test script
4. Verify messages appear instantly in Activity Log tab (no refresh)

## Technical Details

### Implementation Location

**File:** `src/statemachine_engine/database/cli.py`

**Function:** `cmd_send_event(args)`

**Changes:**
- Parse JSON payload string to dict
- Send to WebSocket socket (`/tmp/statemachine-events.sock`)
- Send to machine control socket (if not UI target)
- Enhanced status reporting

### Error Handling

```python
try:
    # Send to WebSocket socket
    sock.sendto(ws_event_msg.encode('utf-8'), websocket_socket_path)
    print("📡 Sent to WebSocket server for real-time UI update")
except Exception as e:
    print(f"⚠️  WebSocket socket unavailable: {e}")
    # Continue anyway (database write still works)
```

### Status Messages

**Success with real-time delivery:**
```
📡 Sent to WebSocket server for real-time UI update
✅ Event sent successfully!
   Event ID: 105
   Target: ui
   Type: activity_log
   Payload: {"message": "Test", "level": "INFO"}
```

**Success with dual-socket:**
```
📡 Sent to WebSocket server for real-time UI update
📡 Sent to worker1 control socket
✅ Event sent successfully!
   Event ID: 106
   Target: worker1
   Type: custom_event
```

**WebSocket unavailable:**
```
⚠️  WebSocket socket unavailable: [Errno 2] No such file or directory
✅ Event sent successfully!
   Event ID: 107
   Target: ui
   Type: activity_log
```

## Benefits

### User Experience
- ✅ Instant feedback in Web UI
- ✅ No manual page refresh needed
- ✅ Real-time activity monitoring
- ✅ Improved debugging experience

### Technical
- ✅ Dual-path reliability (database + socket)
- ✅ Graceful degradation if WebSocket unavailable
- ✅ Zero-copy event delivery
- ✅ Non-blocking socket sends

### Development
- ✅ Fast iteration: send event → see result instantly
- ✅ Better testing workflow
- ✅ Improved observability

## Migration Guide

### No Breaking Changes

Existing scripts continue to work exactly as before. Real-time delivery is automatic if WebSocket server is running.

### Recommended Updates

**Before (still works):**
```bash
statemachine-db send-event --target ui --type activity_log \
  --payload '{"message": "Task done"}'
```

**After (with custom source):**
```bash
statemachine-db send-event --target ui --type activity_log \
  --source my_tool \
  --payload '{"message": "Task done"}'
```

## Troubleshooting

### Messages Not Appearing in UI

**Check WebSocket server is running:**
```bash
ls -la /tmp/statemachine-events.sock
```

**Start WebSocket server:**
```bash
statemachine-ui
```

### Delayed Updates

If messages appear after delay instead of instantly:
- Check WebSocket server is healthy
- Verify browser WebSocket connection
- Check browser console for errors

### Database-Only Mode

If you want database-only (no real-time):
- Stop WebSocket server
- Events still written to database
- UI will show messages after refresh

## Related Documentation

- [Activity Log System](activity-log.md)
- [Unix Socket Communication](unix-sockets.md)
- [WebSocket Server](websocket-server.md)
- [CHANGELOG.md](../CHANGELOG.md) - v0.0.20 release notes

## Version History

- **v0.0.20** (2025-10-11) - Initial real-time delivery implementation
- **v0.0.19** - Database-only send-event
- **v0.0.18** - Basic CLI commands

---

**Author:** State Machine Engine Team
**Updated:** 2025-10-11
**Version:** 0.0.20
