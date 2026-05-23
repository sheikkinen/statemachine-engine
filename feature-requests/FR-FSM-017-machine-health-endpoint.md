# Feature Request: Machine Health HTTP Endpoint

**Priority:** MEDIUM
**Type:** Enhancement
**Status:** Proposed
**Effort:** 0.5 day
**Requested:** 2026-05-09
**Origin:** NC-281 cross-reference — ninchat_voice supervisor health aggregation

## Summary

Add `GET /machines/health` to `monitoring/websocket_server.py` that returns
per-machine liveness status from the `machine_state` DB. Complements the
existing `/health` endpoint (which reports WS server infrastructure) and the
existing `/initial` endpoint (which returns raw machine state snapshots for UI
bootstrap) with an operator-facing health check suitable for load balancers,
Docker `HEALTHCHECK`, and Fly.io `[checks]`.

## Value Statement

Any multi-machine FSM deployment can expose a single HTTP health endpoint that
reports which machines are alive and which are stuck, without coupling to the
WebSocket event stream.

## Problem

The monitoring server has two relevant endpoints today:

| Endpoint | Returns | Suitable for health check? |
|----------|---------|---------------------------|
| `GET /health` | WS server infrastructure (connection count, socket activity) | Partially — tells you the server is alive, not the machines |
| `GET /initial` | All `machine_state` rows (raw DB snapshot) | No — undocumented contract, returns everything |

A Fly.io check or `docker exec curl` needs a single endpoint that answers
"are the expected machines running?". The existing endpoints require the caller
to know FSM internals.

Concrete case: `ninchat_voice` supervisor (`projects/ninchat_voice/`) runs a
custom `/health` route in `supervisor.py` that queries `machine_state` to
aggregate worker liveness. This logic belongs in the monitoring server so every
FSM deployment gets it for free.

## Proposed Solution

Add `GET /machines/health` to `websocket_server.py`:

```python
@app.get("/machines/health")
async def machines_health(stale_after: int = 30):
    """
    Return per-machine liveness derived from machine_state.

    Args:
        stale_after: Seconds since last_activity after which a machine is
                     considered unhealthy (default: 30).

    Returns 200 when all machines are healthy, 503 when any are stale/absent.
    """
    db = Database()
    now = time.time()
    machines = []

    with db._get_connection() as conn:
        rows = conn.execute("""
            SELECT machine_name, current_state, last_activity, config_type
            FROM machine_state
            ORDER BY machine_name
        """).fetchall()

    for row in rows:
        last = row["last_activity"]
        age = round(now - last, 1) if last else None
        healthy = (age is not None) and (age < stale_after)
        machines.append({
            "machine_name": row["machine_name"],
            "current_state": row["current_state"],
            "config_type": row["config_type"],
            "last_activity": last,
            "seconds_since_activity": age,
            "healthy": healthy,
        })

    all_healthy = bool(machines) and all(m["healthy"] for m in machines)
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "healthy": all_healthy,
            "machine_count": len(machines),
            "machines": machines,
            "stale_after_seconds": stale_after,
            "timestamp": now,
        },
    )
```

### Design decisions

**`stale_after` as query param, not config:** The monitoring server has no
concept of expected machine count or names — it serves whatever is in the DB.
The operator controls the liveness threshold at call time. Fly.io health check
can hard-code `?stale_after=60`; a tight integration test can use `?stale_after=5`.

**503 on any unhealthy, not 200+body flag:** Load balancers and `docker
inspect` keyed on HTTP status codes, not JSON content. Return 503 so the check
fails fast without parsing.

**Empty DB → 503:** Zero machines means the engines haven't started yet or all
crashed. Treat as unhealthy by default. Caller can use `stale_after=0` to
suppress the check if they expect an empty DB on cold start.

**No `machine_name` filter param in this FR:** Filtering by name or
`config_type` can be a follow-on. The base endpoint covers 95% of uses.

## Acceptance Criteria

- [ ] `GET /machines/health` returns 200 when all DB machines have
      `last_activity` within `stale_after` seconds
- [ ] Returns 503 when any machine is stale or when machine table is empty
- [ ] `stale_after` query param accepted, default 30
- [ ] Each machine entry includes `machine_name`, `current_state`,
      `config_type`, `seconds_since_activity`, `healthy`
- [ ] Existing `/health` and `/initial` endpoints unchanged
- [ ] Tests: mock DB with fresh machines → 200; one stale machine → 503;
      empty table → 503
- [ ] `README.md` for monitoring server updated with endpoint table

## Alternatives Considered

| Approach | Verdict |
|----------|---------|
| Enhance existing `/health` to include machine data | Rejected — changes the contract of an infrastructure endpoint; monitoring tools keyed on it would break |
| Rename `/initial` → `/machines` and add health flags | Rejected — `/initial` is a WebSocket handshake optimisation, not a health API |
| New standalone health server process | Rejected — adds operational complexity; monitoring server already has FastAPI |
| Keep in application layer (ninchat_voice supervisor.py) | Rejected — zero voice-specific knowledge required; duplicates DB query logic across projects |

## Related

- `src/statemachine_engine/monitoring/websocket_server.py` — target file
  (existing `/health` at line 678; `/initial` at line 692; `get_initial_state`
  at line 363 — shares the DB query pattern)
- `src/statemachine_engine/database/models.py` — `Database()` class
- `docs/parallel-state-machines.md` — multi-machine deployment context
- FR-FSM-016 — event-driven job completion (companion: push vs pull)
- FR-FSM-018 — supervisor-as-FSM example (first consumer of this endpoint)
- `projects/ninchat_voice/docs/NC-281-supervisor-monitoring.md` — origin:
  the supervisor `/health` route that triggered this FR
