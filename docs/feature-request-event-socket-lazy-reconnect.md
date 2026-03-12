# Feature Request: EventSocketManager lazy reconnect on emit()

**Status:** Enforced — shipped v1.0.75
**Judged:** 2026-03-12

## Problem

`EventSocketManager._connect()` is called once at `__init__()`. If the websocket
server's Unix socket does not exist at that moment (e.g. because supervisord starts
processes in parallel and the engine wins the race), `self.sock = None` permanently.

Every subsequent `emit()` call hits:

```python
if not self.sock:
    self.logger.debug(f"📭 Socket not connected, cannot emit: ...")
    return False
```

The `_connect()` retry on line 83 only fires when `sock.send()` raises — it is
unreachable when `self.sock is None`. The log message is at DEBUG level, invisible
at INFO. The engine silently drops every event for its entire lifetime.

## Consequences observed (ninchat_voice / fly.io)

- `machine_registered` never emitted → monitoring UI status panel frozen
- No state transitions visible in UI during or after calls
- The workaround was a supervisord poll-wait wrapper:
  `until test -S /tmp/statemachine-events.sock; do sleep 0.2; done`
  This is fragile: it protects only against startup race, not against websocket-server
  restarts (autorestart=true) after the engine is already running.

## Proposed fix

Add a lazy reconnect inside `emit()` when `self.sock is None`:

```python
def emit(self, event_data: dict) -> bool:
    if not self.sock:
        self._connect()          # <-- retry before giving up
    if not self.sock:
        self.logger.warning(     # <-- WARNING not DEBUG: silent drop is a defect
            f"📭 Socket not connected, dropping {event_data.get('type', 'unknown')}"
        )
        return False
    ...
```

Also raise the log level from DEBUG to WARNING so silent drops are visible in
production logs at the default INFO threshold.

## Acceptance criteria

1. If `_connect()` fails at init (socket not yet created), `emit()` retries
   `_connect()` on each call until the socket appears (lazy reconnect).
2. When an event is dropped due to no socket, it is logged at WARNING, not DEBUG.
3. Engine survives websocket-server restart: after the server restarts and recreates
   its socket, the next `emit()` reconnects transparently.
4. Unit test: engine started before websocket socket exists, socket created after 2s,
   emit() called after socket creation → event delivered.

## Workaround in place

`supervisord.conf` wraps the engine command with a poll loop:
```
command=/bin/sh -c 'until test -S /tmp/statemachine-events.sock; do sleep 0.2; done;
  exec statemachine ...'
```
This handles startup race but not runtime restarts of the websocket-server process.
The proper fix belongs in `EventSocketManager`, not in the deployment config.

## Judgement Notes

### Refinements required (not in original proposal)

1. **Socket fd leak in `_connect()`.** Current code creates `socket.socket()` then
   on failure sets `self.sock = None` — the fd is never closed. Fix: create into a
   local, close on failure, only assign to `self.sock` on success.

2. **Reconnect spam risk.** If websocket server is down for minutes, every `emit()`
   call (every ~50ms state transition) would attempt `_connect()` + log WARNING.
   Rate-limit: attempt reconnect at most once per 5 seconds.

3. **Log level nuance.** WARNING on reconnect-attempt failure (actionable). DEBUG
   on "still no sock" early return between attempts (noise suppression).

4. **Acceptance criterion 4 is an integration test**, not a unit test. Use mocking
   to simulate delayed socket availability without real sockets or sleeps.

### Frozen scope

**Production changes (`EventSocketManager`):**
- Fix socket fd leak in `_connect()` (close on failure)
- Add `self._last_connect_attempt = 0.0` to `__init__`
- Lazy reconnect in `emit()` with 5s rate limit
- WARNING on reconnect failure; DEBUG on subsequent drops until next attempt

**Tests (4):**
1. `test_emit_retries_connect_when_sock_is_none`
2. `test_emit_drops_logged_at_warning`
3. `test_reconnect_rate_limited`
4. `test_connect_closes_socket_on_failure`
