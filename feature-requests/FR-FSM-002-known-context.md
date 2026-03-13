# Feature Request: Linter False Positive Reduction (known_context)

**Priority:** HIGH
**Type:** Enhancement
**Status:** Proposed
**Effort:** 1 day
**Requested:** 2026-03-13

## Summary

Reduce E012/W009 false positives by teaching the linter about runtime-injected
context variables: initial context passed at spawn, `store_as` patterns in
actions, and direct payload access.

## Value Statement

Config authors see only genuine errors instead of 16 false positives from
runtime context, making the linter trustworthy enough for CI enforcement.

## Problem

E012 accounts for **16 of 39 errors** (41%) across example configs — all false
positives from three runtime injection patterns the linter cannot see statically:

| Pattern | Example | Affected Config |
|---------|---------|-----------------|
| Initial context at spawn | `{report_id}`, `{report_title}` | patient-records.yaml |
| `store_as` in actions | `{current_job.job_id}` via pop_from_list | concurrent-controller.yaml |
| Direct payload access | `{payload.machine}`, `{payload.job_id}` | controller.yaml |

W009 duplicates many of these as warnings (5 additional findings).

## Proposed Solution

### 1. `known_context` YAML key

Allow configs to declare variables available at runtime:

```yaml
# New top-level key
known_context:
  - report_id        # Passed via --initial-context at spawn
  - report_title
  - current_job      # Set by pop_from_list store_as
  - payload          # Available in event handler scope
```

E012/W009 treat `known_context` entries as valid context keys alongside
`STANDARD_CONTEXT_KEYS` and context_map promotions.

### 2. `store_as` recognition

Teach the linter to scan action configs for `store_as` fields. When found,
the target key becomes a known context variable:

```python
# In checks_semantic.py or checks_actions.py
for action in action_list:
    store_as = action.get("store_as")
    if store_as:
        known_keys.add(store_as)
```

Actions with `store_as`: `pop_from_list`, `get_pending_jobs`, `claim_job`.

### 3. `payload` as implicit context

The engine makes the event payload available as `payload` during action
execution. Add `payload` to `STANDARD_CONTEXT_KEYS`.

## Acceptance Criteria

- [ ] `known_context` YAML key parsed and used by E012/W009
- [ ] `store_as` fields in action configs recognized as context promoters
- [ ] `payload` added to STANDARD_CONTEXT_KEYS
- [ ] E012 count drops from 16 to 0 on existing example configs
- [ ] W009 count drops from 5 to 0 on existing example configs
- [ ] Unit tests for each new context source
- [ ] No regressions in existing 67 linter tests

## Alternatives Considered

**Suppress E012 globally:** Rejected — hides real bugs alongside false positives.

**Per-file `# noqa` comments in YAML:** Not supported by YAML; would require
custom comment parsing.

**Infer from action execution order:** Too complex — would need full dataflow
analysis within a state's action sequence.

## Related

- FR-FSM-001 — Graph linter (parent feature)
- `tools/linter/checks_semantic.py` — E012/W009 implementation
- `core/engine.py` — runtime context injection
- Diary seed: "Should the engine export CONTEXT_KEYS programmatically?"
