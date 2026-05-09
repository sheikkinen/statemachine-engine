# Feature Request: First-Class state_groups in YAML Config

**Priority:** HIGH
**Type:** Enhancement
**Status:** Proposed
**Effort:** 1 day
**Requested:** 2026-04-28

## Summary

Replace comment-based state group parsing (`# === GROUP NAME ===`) with a
first-class `state_groups:` YAML key. State groups are structural metadata that
drive diagram generation, UI composite views, and future validation — they
should not live in comments that YAML parsers discard.

## Value Statement

Config authors get validated, discoverable state groups instead of relying on a
fragile comment convention that breaks on round-trip, is invisible to YAML
tooling, and is duplicated across two parsers.

## Problem

State groups are currently extracted by line-by-line text parsing of raw YAML
files, looking for `# === GROUP NAME ===` comment patterns. This causes:

1. **Invisible to schema validation** — `statemachine-validate` cannot check
   that every state belongs to a group, or that group names are unique, because
   comments are not data.
2. **Fragile** — any YAML formatter, round-trip library (ruamel), or editor
   auto-format strips or reflows comments, silently destroying group definitions.
3. **Undiscoverable** — new users must read engine source (`config.py:50-88` or
   `diagrams.py:222-260`) to learn the convention. It is not in `--help`, schema
   docs, or validation output.
4. **Duplicated parser** — `parse_state_groups()` is copy-pasted identically in
   both `tools/config.py` and `tools/diagrams.py` (40 lines × 2).
5. **No ungrouped-state detection** — states listed outside any `# ===` block
   silently fall into no group, producing incomplete diagrams with no warning.
6. **Cannot be programmatically generated** — tools that create or modify
   configs (templates, project scaffolding, FR-FSM-011) cannot set state groups
   through the YAML API.

## Proposed Solution

Add a top-level `state_groups:` key to the config schema:

```yaml
# BEFORE (comment-based, fragile)
states:
  # === OPERATIONAL ===
  - idle
  - syncing_inbox
  - processing_topic
  # === TERMINAL ===
  - stopped

# AFTER (first-class, validated)
states:
  - idle
  - syncing_inbox
  - processing_topic
  - stopped

state_groups:
  OPERATIONAL:
    - idle
    - syncing_inbox
    - processing_topic
  TERMINAL:
    - stopped
```

### Implementation

1. **Schema**: Add `state_groups` as optional `dict[str, list[str]]` to config
   schema. Each key is a group name, each value is a list of state names.

2. **Validation** (`statemachine-validate`):
   - Every state in `state_groups` must exist in `states`.
   - Every state in `states` must appear in exactly one group (warn if ungrouped).
   - Group names must be unique.
   - No empty groups.

3. **Parser consolidation**: Replace both `parse_state_groups()` functions with
   a single `config["state_groups"]` dict lookup. Delete the line-by-line text
   parser.

4. **Fallback period**: If `state_groups:` key is absent, fall back to comment
   parsing with a deprecation warning: "state_groups should be defined as a YAML
   key, not comments. See migration guide."

5. **Migration helper**: `statemachine-validate --fix` auto-generates the
   `state_groups:` key from existing comments (one-time migration).

6. **Diagram generation**: `statemachine-diagrams` reads `config["state_groups"]`
   directly — no file re-parsing needed.

## Acceptance Criteria

- [ ] `state_groups:` key accepted and validated by `statemachine-validate`
- [ ] Validation errors for: state not in `states`, duplicate state across groups, empty group
- [ ] Warning for states not assigned to any group
- [ ] `statemachine-diagrams` generates identical output from YAML key as from comments
- [ ] Duplicate `parse_state_groups()` in `config.py` and `diagrams.py` removed
- [ ] Comment-based parsing retained as deprecated fallback with warning
- [ ] `statemachine-validate --fix` migrates comments to YAML key
- [ ] Tests added for validation, migration, and diagram generation
- [ ] Existing configs with comment-based groups continue to work (deprecation, not breakage)

## Alternatives Considered

**Keep comment convention, add documentation:** Rejected — documentation doesn't
fix round-trip breakage, schema invisibility, or parser duplication. The root
cause is that structural data lives in comments.

**Nested states under groups:** e.g. `states: { OPERATIONAL: [idle, ...] }`.
Rejected — changes the shape of `states` which is consumed everywhere. A
parallel `state_groups` key is additive and non-breaking.

## Related

- FR-FSM-006: Split `tools/diagrams.py` (where one copy of the parser lives)
- FR-FSM-011: Project manifest system (needs programmatic state group access)
- `tools/config.py:50-88`: First copy of `parse_state_groups()`
- `tools/diagrams.py:222-260`: Second copy of `parse_state_groups()`
