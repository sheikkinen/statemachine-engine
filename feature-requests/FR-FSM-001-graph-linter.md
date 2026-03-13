# Feature Request: FSM Graph Linter

**Priority:** MEDIUM
**Type:** Feature
**Status:** Proposed
**Effort:** 3 days
**Requested:** 2026-03-13

## Summary

Build a dedicated linter for FSM YAML state machine configurations, modeled
after the YAMLGraph `graph lint` architecture. The linter validates structural
correctness, cross-references, reachability, action-emission consistency, and
silent misconfigurations — catching defects before runtime.

## Value Statement

FSM authors get immediate, actionable feedback on broken transitions, orphaned
states, undeclared events, and silent misconfigurations, reducing debug cycles
from minutes of runtime tracing to seconds of static analysis.

## Problem

The existing `statemachine-validate` tool (`tools/validate.py`) performs 8
checks focused on event/transition consistency. Several important defect
categories are not covered:

| Gap | Impact |
|-----|--------|
| No terminal-state reachability | State machines can get stuck with no path to completion |
| No action config validation | Misspelled action types, missing required fields silently fail at runtime |
| No cycle detection | Unguarded loops spin forever without warning |
| No context_map validation | NC-120 `context_map` (property of event config entries, maps `context_key → payload_path`) not verified |
| No file-reference validation | `actions_root`, custom action paths not checked on disk |
| No silent-misconfig detection | Unused config keys, wrong nesting silently ignored |
| No interpolation variable validation | `{variable}` references in action configs not checked against known context keys |

The YAMLGraph linter (`yamlgraph/linter/`) demonstrates the architecture:
standalone check functions returning `LintIssue` objects, orchestrated by a
central runner, with error codes (E=error, W=warning) and machine-readable
output. The FSM linter should follow this pattern adapted to the FSM domain.

## Proposed Solution

### Architecture

```
CLI Entry Point
  statemachine-lint examples/*/config/*.yaml   (new CLI command)

Linter Core
  tools/linter/__init__.py               → public API: lint_config(), LintIssue
  tools/linter/core.py                   → orchestrator: calls all checks, returns LintResult
  tools/linter/checks_structural.py      → E001–E005: structural validation
  tools/linter/checks_reachability.py    → E006–E007, W001–W003: graph traversal
  tools/linter/checks_actions.py         → E008–E011, W004–W006: action config validation
  tools/linter/checks_semantic.py        → E012–E015, W007–W010: cross-reference & expression
```

### Check Inventory

#### Structural Checks (checks_structural.py)

| Code | Severity | Check |
|------|----------|-------|
| **E001** | error | `initial_state` not defined or not in states list |
| **E002** | error | Transition references undefined state (`from` or `to`) |
| **E003** | error | Event used in transition not declared in `events` list |
| **E004** | error | Duplicate state name |
| **E005** | error | Duplicate transition (same from + event + to) |

#### Reachability Checks (checks_reachability.py)

| Code | Severity | Check |
|------|----------|-------|
| **E006** | error | No terminal state reachable from `initial_state` (dead-end machine) |
| **E007** | error | State has no outgoing transitions and is not a terminal state (hardcoded: `stopped`, `shutdown`, `completed`) |
| **W001** | warning | State not reachable from `initial_state` (orphaned) |
| **W002** | warning | State reachable only via wildcard `from: *` |
| **W003** | warning | More than 5 wildcard transitions (excessive wildcards) |

#### Action Checks (checks_actions.py)

| Code | Severity | Check |
|------|----------|-------|
| **E008** | error | Action `type` not in known built-in types (14 pluggable + 2 inline: `log`, `sleep`) or discoverable via `actions_root` |
| **E009** | error | Action emits success/failure event with no corresponding transition |
| **E010** | error | Required action config field missing (e.g., `bash` action missing `command`) |
| **E011** | error | `context_map` key references unknown context variable (not promoted by any prior event) |
| **W004** | warning | Action config contains unknown keys (possible typo) |
| **W005** | warning | `sleep` action duration > 300s (likely misconfiguration) |
| **W006** | warning | `bash` action command contains unescaped shell expansion |

#### Semantic & Cross-Reference Checks (checks_semantic.py)

| Code | Severity | Check |
|------|----------|-------|
| **E012** | error | `{variable}` interpolation references undeclared context key |
| **E013** | error | `context_map` payload path uses invalid syntax |
| **E014** | error | `context_map` payload path uses dot notation deeper than event payload supports |
| **E015** | error | Circular context_map dependency (A promotes from B which promotes from A) |
| **W007** | warning | Event declared but never used in any transition |
| **W008** | warning | State has actions but all paths exit via `error` event only |
| **W009** | warning | Interpolation `{variable}` used but no event promotes `variable` via context_map |
| **W010** | warning | Self-transition without action (infinite idle loop) |

### Data Model

```python
from pydantic import BaseModel
from enum import Enum
from pathlib import Path

class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"

class LintIssue(BaseModel):
    code: str                        # e.g. "E001"
    severity: Severity
    message: str                     # human-readable description
    file: Path                       # YAML file path
    context: str | None = None       # state/event/action name for context
    fix: str | None = None           # suggested fix

class LintResult(BaseModel):
    issues: list[LintIssue]
    error_count: int
    warning_count: int
```

### CLI Interface

```bash
# Lint all configs
statemachine-lint examples/*/config/*.yaml

# Strict mode (warnings are errors)
statemachine-lint --strict examples/*/config/*.yaml

# JSON output for CI integration
statemachine-lint --format json examples/*/config/*.yaml

# Specific check only
statemachine-lint --select E001,E002,W001 examples/*/config/*.yaml
```

### Example Output

```
$ statemachine-lint examples/worker/config/worker.yaml

examples/worker/config/worker.yaml
  ✗ [E002] Transition references undefined state 'PROCESING' (from: IDLE, event: start) — did you mean 'PROCESSING'?
  ✗ [E009] Action 'process_data' emits 'data_ready' but no transition handles it from state 'PROCESSING'
  ⚠ [W001] State 'LEGACY_CLEANUP' not reachable from initial state 'IDLE'
  ⚠ [W007] Event 'manual_reset' declared but never used in any transition

2 errors, 2 warnings
```

### Relationship to Existing validate.py

The linter **subsumes** `tools/validate.py`. The 8 existing checks map to:

| validate.py check | Linter equivalent |
|---|---|
| `_check_initial_state` | E001 |
| `_check_missing_events` | E003 |
| `_check_event_coverage` | W007 |
| `_check_action_emissions` | E009 |
| `_check_standard_patterns` | E010 (generalized) |
| `_check_orphaned_states` | W001 |
| `_check_unreachable_states` | W001 (unified) |
| `_check_wildcard_transitions` | W003 |

After the linter ships, `validate.py` becomes a thin wrapper calling
`lint_config()` with `--select` for its original checks, preserving the
existing CLI interface.

## Acceptance Criteria

- [ ] `tools/linter/` package exists with `__init__.py`, `core.py`, and 4
      check modules
- [ ] `LintIssue` and `LintResult` are Pydantic models
- [ ] All 15 error checks (E001–E015) implemented with unit tests
- [ ] All 10 warning checks (W001–W010) implemented with unit tests
- [ ] `statemachine-lint` CLI entry point added to `pyproject.toml`
- [ ] Supports `--strict`, `--format json`, `--select` flags
- [ ] Existing `validate.py` checks preserved (thin wrapper or verified
      equivalent coverage)
- [ ] At least 3 real config files (`examples/*/config/*.yaml`) lint cleanly
- [ ] Pre-commit hook `statemachine-lint` added to `.pre-commit-config.yaml`
- [ ] README.md updated with linter usage section
- [ ] All checks have unique error codes following `E0XX`/`W0XX` convention

## Implementation Notes

### Terminal States
The engine hardcodes terminal states as `["stopped", "shutdown", "completed"]`
in `engine.py`. E006/E007 must use this list (or make it configurable via YAML
`terminal_states` key) rather than guessing.

### Inline vs Pluggable Actions
The engine handles `log` and `sleep` actions inline (directly in engine.py),
not via the `ActionLoader` plugin system. E008 must include these two inline
types in the known-actions list alongside the 14 pluggable built-in actions
and the `activity_log` → `log` alias.

### Interpolation Syntax
The engine uses `{variable}` syntax (regex: `r"\{([a-zA-Z_][a-zA-Z0-9_.]*)\}"`)
for string interpolation in action configs. This is NOT `${context.X}` or
Jinja2 syntax. E012/W009 must match the actual engine regex.

### context_map Model
`context_map` is a property OF individual event configuration entries, not a
standalone top-level dict. It maps `context_key → payload_path`, extracting
values from event payloads into the FSM context. E011/E013/E014 must traverse
event configs to find `context_map` entries.

## Alternatives Considered

**Extend `validate.py` directly:** Rejected — the module is already at 512
lines and would balloon past 800. A dedicated `linter/` package with separate
check modules is more maintainable and follows the YAMLGraph pattern.

**Use YAMLGraph linter as-is:** Rejected — the FSM domain model (states,
transitions, events, actions) is fundamentally different from the YAMLGraph
domain (nodes, edges, prompts, tools). The architecture is transferable; the
checks are not.

**JSON Schema validation only:** Rejected — JSON Schema catches type errors
but cannot validate cross-references (state exists, event has transition),
reachability, or action-emission consistency. A programmatic linter is
required for semantic checks.

**Integrate into engine load_config():** Rejected — mixing validation with
loading couples concerns. The linter should be a standalone tool runnable
without starting the engine.

## Related

- `tools/validate.py` — existing validation (8 checks), to be wrapped
- `yamlgraph/linter/` — architecture inspiration (48 checks across 6 modules)
- `FR-186` — pre-commit quality gates (hook slot ready)
- `NC-120` — context_map feature (E011, E013, E014 validate its config; note: `context_map` is a property OF event config entries, mapping `context_key → payload_path`)
- `.pre-commit-config.yaml` — hook registration target
- YAMLGraph linter checks reference: `yamlgraph/linter/checks.py`,
  `checks_semantic.py`, `checks_contracts.py`, `checks_providers.py`
