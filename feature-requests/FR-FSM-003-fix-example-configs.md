# Feature Request: Fix Example Config Lint Errors

**Priority:** MEDIUM
**Type:** Bug
**Status:** Proposed
**Effort:** 0.5 days
**Requested:** 2026-03-13

## Summary

Fix genuine lint errors in example FSM configs discovered by the FR-FSM-001
graph linter. Clean configs serve as documentation and CI-lintable references.

## Value Statement

Example configs become trustworthy documentation — every example lints clean,
proving patterns work and serving as regression tests for the linter itself.

## Problem

The linter found **39 errors, 16 warnings** across 7 example configs. After
FR-FSM-002 eliminates E012/W009 false positives (~21 findings), roughly 18
genuine errors remain:

| Config | Errors | Key Issues |
|--------|--------|------------|
| custom_actions/worker.yaml | 18 | Missing states/events lists, no actions_root |
| concurrent-controller.yaml | 3 | No terminal state, dead events (E006, E009) |
| controller.yaml | 1 | Obsolete `check_events` action type (E008) |
| patient-records.yaml | 1 | `complete_job` emits unhandled event (E009) |

## Proposed Solution

### custom_actions/worker.yaml
- Add `states: [waiting, greeting, calculating, completed]`
- Add `events: [greet, greeted, calculate, calculated, stop]`
- Add `actions_root: actions/` so E008 can discover `greet` and `calculate`

### concurrent-controller.yaml
- Add `stopped` to states + transition from `*` to `stopped` on `stop` event
- Add transitions for `has_job` and `job_claimed` events, or remove from events list

### controller.yaml
- Replace `check_events` with appropriate built-in action or add `actions_root`

### patient-records.yaml
- Add transition from `ready` on `job_completed` event (to `shutdown` or self-loop)

## Acceptance Criteria

- [ ] All 7 example configs lint with 0 errors (after FR-FSM-002)
- [ ] Warnings ≤ 5 total (W002 for wildcard-only reach is acceptable)
- [ ] No behavioral changes — configs must still run correctly
- [ ] `statemachine-lint --strict` passes on simple_worker and timeout_demo

## Alternatives Considered

**Suppress with known_context only:** Doesn't fix genuine structural bugs
like missing states lists or dead events.

**Delete broken examples:** Rejected — they demonstrate real patterns
(custom actions, concurrent controllers) worth preserving.

## Related

- FR-FSM-001 — Graph linter
- FR-FSM-002 — known_context (prerequisite — must land first to separate
  false positives from real bugs)
