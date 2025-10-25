# WebSocket Communications - Implementation Plan (Revised)

## Current Situation

**Problem**: Python WebSocket server (670+ lines) is complex and had blocking issues.

**Constraint**: Python state machines use **SOCK_DGRAM** (Unix datagram sockets) which Node.js doesn't natively support without compilation.

**Decision**: Keep Python WebSocket server, but simplify and fix it.

## Why Not Node.js?

1. **DGRAM Incompatibility**: Node.js doesn't support Unix DGRAM sockets natively
2. **unix-dgram package**: Requires native compilation (node-gyp), fails on some systems
3. **Protocol Mismatch**: Would require changing all Python engines to SOCK_STREAM
4. **Multi-machine**: Python engines communicate with each other via DGRAM

## Revised Plan: Simplify Python WebSocket Server

### Goals

1. Keep the working DGRAM socket listener
2. Remove unnecessary complexity (watchdog, monitors)
3. Fix any remaining blocking issues
4. Document the zero-copy optimization

### Option 1: Keep Existing Python Server

**Status**: Already working, already fixed (v1.0.26)

**What it does right:**
- ✅ SOCK_DGRAM listener works
- ✅ WebSocket broadcasts work
- ✅ Ping/pong works
- ✅ Zero-copy optimization (pre-serialize JSON)
- ✅ All blocking issues fixed

**Keep it as-is**: Already functional and battle-tested.

### Option 2: Simplify Python Server (Future)

If simplification is needed later:

**File: `src/statemachine_engine/monitoring/websocket_server.py`**

**Simplifications:**
1. Remove watchdog thread (overhead)
2. Remove performance monitor (not needed)
3. Remove database polling fallback (trust Unix socket)
4. Keep essential: DGRAM listener, WebSocket broadcast, ping/pong

**Estimated reduction**: 670 lines → ~300 lines

## Current Architecture (Working)

```
State Machines → Unix DGRAM Socket → Python WebSocket Server → Browser
                 (/tmp/*.sock)        (FastAPI/Starlette)      (ws://3002)
```

## What We Learned

1. **SOCK_DGRAM is required** for multi-machine communication
2. **Node.js can't easily do DGRAM** without native compilation
3. **Python server works** - it had blocking issues, but they're fixed
4. **Zero-copy works in Python too** - pre-serialize before sending

## Recommendation

**Keep the Python WebSocket server** - it works, it's fixed, and it supports the DGRAM protocol that state machines require.

**No changes needed** unless:
- Want to reduce complexity (remove watchdog/monitors)
- Want to switch entire system to SOCK_STREAM (big change)
- Find new blocking issues

## Alternative: Node.js with Protocol Change

If Node.js is absolutely required, would need:

1. **Change all Python engines**: SOCK_DGRAM → SOCK_STREAM
2. **Add message framing**: Newline-delimited JSON
3. **Update all send_event calls**: Add framing
4. **Test all inter-machine communication**

**Estimated effort**: 2-3 hours, affects 10+ files

**Risk**: High - breaks existing state machines

## Conclusion

**Status**: Python WebSocket server is working and optimized.

**Action**: Document current architecture, no implementation needed.

**Future**: Consider Node.js if/when state machines switch to SOCK_STREAM.

---

**End of Revised Plan**
