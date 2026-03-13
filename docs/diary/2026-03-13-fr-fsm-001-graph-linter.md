# Diary: FR-FSM-001 — FSM Graph Linter

**Date:** 2026-03-13
**Feature:** FR-FSM-001 — 25-check FSM graph linter
**Version:** v1.0.77

## Cognitive Process

### Trap: Plausible Wrong Answer in the FR
The original FR claimed field names (`key`, `config`, `event`) that appeared reasonable
but were wrong when checked against actual action implementations. `pop_from_list` uses
`list_key`, `start_fsm` uses `yaml_path`, `send_event` uses `event_type`. The judgement
phase caught these before enforcement — **the cheapest bug is the one killed in the spec**.

### Trap: Downstream Fix Temptation
When real configs showed false positives (W004 for `get_pending_jobs` with `store_as`,
`claim_job` with `already_claimed`), the temptation was to suppress the warnings.
Instead, the fix was to **expand the known-keys registry at the boundary** — the
TYPE_SPECIFIC_KEYS dict — rather than add exception logic in the check function.
Normalize at the boundary.

### Insight: actions_root Discovery
The `custom_actions` example exercises a pattern where action types are loaded from
a filesystem directory. A linter that only knows built-ins would flag every custom
action as E008. Adding `_discover_custom_actions()` to read the `actions_root`
directory at lint time eliminated false positives without hardcoding anything.

### Insight: Context Key Boundaries
The E012/W009 checks expose a real architectural gap: the engine provides certain
context keys (id, job_id, machine_name) implicitly, and context_map promotes others
explicitly, but there's no single source of truth for "what keys are available."
The linter had to define `STANDARD_CONTEXT_KEYS` — which is itself a form of
documentation-as-code.

### Process: TDD Discipline Held
67 tests written RED before any implementation. All 67 passed GREEN on first run
after implementing all 4 check modules. The test-first approach forced each check
to have a clear, testable specification before code existed.

## Metrics
- **Tests:** 67 new (390 total, 0 failures)
- **Checks:** 15 errors (E001–E015) + 10 warnings (W001–W010) = 25
- **Modules:** 8 files in tools/linter/ (models, 4 checks, core, cli, __init__)
- **Real configs:** 3 lint clean, 4 with genuine issues found

## Seed
When `STANDARD_CONTEXT_KEYS` drifts from the engine's actual context initialization,
E012/W009 will produce false positives. Should the engine export its known context
keys programmatically — perhaps a `Engine.CONTEXT_KEYS` class attribute — so the
linter can import truth rather than maintaining a parallel list?
