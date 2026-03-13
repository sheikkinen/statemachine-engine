# Feature Request: Split monitoring/websocket_server.py

**Priority:** LOW
**Type:** Enhancement
**Status:** Proposed
**Effort:** 0.5 days
**Requested:** 2026-03-13

## Summary

Split `monitoring/websocket_server.py` (723 lines — 1.6x the 450-line limit)
into protocol handling and server management submodules.

## Value Statement

WebSocket server code becomes modular — protocol handling, client management,
and message routing can be understood and tested independently.

## Problem

`monitoring/websocket_server.py` at 723 lines exceeds the 450-line limit by
1.6x. It combines WebSocket protocol handling, client connection management,
message routing, and server lifecycle in a single file.

## Proposed Solution

Split into a `monitoring/websocket/` package:

```
monitoring/websocket/__init__.py  → public API, WebSocketServer class (~80 lines)
monitoring/websocket/server.py    → Server lifecycle, startup/shutdown
monitoring/websocket/protocol.py  → Message parsing, routing, protocol handling
monitoring/websocket/clients.py   → Client connection management, broadcasting
```

## Acceptance Criteria

- [ ] `monitoring/websocket_server.py` replaced by `monitoring/websocket/` package
- [ ] All submodules < 400 lines
- [ ] WebSocket server behavior unchanged
- [ ] All existing tests pass
- [ ] Pre-commit file-size-gate exclusion for `monitoring/websocket_server.py` removed

## Alternatives Considered

**Trim logging/comments:** Insufficient — even aggressive trimming won't
bring 723 lines under 450 without splitting responsibilities.

## Related

- FR-186 — Pre-commit quality gates (file-size-gate exempts this file)
- `.pre-commit-config.yaml` — exclusion list to update
