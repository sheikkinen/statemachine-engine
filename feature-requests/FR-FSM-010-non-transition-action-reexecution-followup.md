# Feature Request: VB-006 Non-Transition Action Re-Execution Follow-Up

**Priority:** HIGH
**Type:** Bug
**Status:** Enforced ✅ (retroactive)
**Effort:** 0.5 day
**Requested:** 2026-03-16
**Judged:** 2026-03-16

## Summary

Document and formalize the VB-006 behavior already implemented in
`StateMachineEngine._execute_state_actions()`: non-transition actions are
one-shot per state entry by default, while repeat-per-tick behavior requires
explicit opt-in (`repeatable: true` or `run_policy: repeat_per_tick`).

## Value Statement

FSM authors get predictable, safe action execution defaults that prevent
accidental repeated side effects while preserving explicit polling behavior.

## Problem

The original FR-FSM-009 focused on transition-triggering action idempotency.
The follow-up behavior for non-transition actions was implemented in code, but
needed explicit FR-level traceability to clarify:

- default policy for non-transition actions
- opt-in mechanism for repeat-per-tick polling
- expected runtime semantics in `_execute_state_actions()`

Without an explicit FR record, the behavior is harder to audit and easier to
misinterpret as incidental implementation detail.

## Proposed Solution

Treat this as a retroactive formalization of the implemented policy:

1. Keep action execution one-shot per state entry by default.
2. Preserve repeat-per-tick only for actions that explicitly opt in.
3. Define opt-in keys:
   - `repeatable: true`
   - `run_policy: repeat_per_tick` (or `repeat` alias)
4. Keep transition-based mid-sequence abort and completion tracking unchanged.

Code reference:

- `src/statemachine_engine/core/engine.py`
  - `_execute_state_actions()`
  - `_is_repeatable_action()`

## Acceptance Criteria

- [x] Non-transition actions are marked completed after first execution in a state entry.
- [x] Actions with `repeatable: true` execute on every tick.
- [x] Actions with `run_policy: repeat_per_tick` execute on every tick.
- [x] Transition-triggering actions remain one-shot per entry via generation tracking.
- [x] Existing idempotency tests pass.
- [x] Retroactive FR created for traceability.

## Verification

- Focused test module passes:
  - `tests/core/test_action_idempotency.py` (10 passed)

## Alternatives Considered

- Leave behavior undocumented in FR history.
  - Rejected: reduces auditability and makes policy intent ambiguous.

- Introduce a new YAML key for repeat policy only.
  - Rejected: current dual-key support already implemented and tested.

## Related

- `feature-requests/FR-FSM-009-action-idempotency.md`
- `tests/core/test_action_idempotency.py`
- `src/statemachine_engine/core/engine.py`

---

## Judgement (2026-03-16)

**Verdict: APPROVED with 2 mandatory amendments.**

The FR intent is strong and the runtime policy is correctly described, but two
traceability/correctness gaps remain.

### Amendment 1: Add explicit test coverage for `run_policy: repeat_per_tick`

The acceptance criteria claims this behavior is verified, but
`tests/core/test_action_idempotency.py` currently only covers
`repeatable: True` and does not assert `run_policy: repeat_per_tick`.

**Required update:** add a unit test that configures an action with
`run_policy: "repeat_per_tick"` and proves repeat execution across ticks.

### Amendment 2: Clarify or harden `repeatable` boolean coercion

Current implementation in `_is_repeatable_action()` uses:

```python
if bool(action_config.get("repeatable", False)):
  return True
```

This treats non-empty strings (including `"false"`) as truthy, which can
accidentally enable repeat-per-tick behavior when interpolated/string values
flow into config.

**Required update (choose one):**

1. Harden implementation to parse booleans explicitly (`True`, `"true"`, etc.),
   with `"false"` correctly treated as false.
2. If coercion is intentional, document the exact truthiness contract and add
   tests proving accepted/rejected values.

### Post-amendment status criteria

After both amendments are implemented and validated, this FR can be moved to:

- `Status: Enforced ✅ (retroactive)`

## Enforcement (2026-03-16)

Both mandatory amendments from Judgement were implemented and validated.

1. Amendment 1 completed: explicit `run_policy: repeat_per_tick` coverage added.
  - Test: `test_run_policy_repeat_per_tick_repeats_every_tick`
2. Amendment 2 completed: `repeatable` coercion hardened to parse boolean-like
  string values explicitly.
  - Test: `test_repeatable_string_false_does_not_repeat`

Validation:

- `tests/core/test_action_idempotency.py` -> `10 passed`
