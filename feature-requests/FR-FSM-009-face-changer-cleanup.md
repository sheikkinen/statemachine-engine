# Feature Request: Face-Changer Remnant Cleanup

**Priority:** LOW
**Type:** Enhancement
**Status:** Proposed
**Effort:** 0.5 days
**Requested:** 2026-03-14

## Summary

Remove face-changer domain-specific references from the genericized statemachine-engine codebase.

## Value Statement

New users of the generic FSM engine get a clean codebase without confusing references to an obsolete domain (face-changer), reducing onboarding friction.

## Problem

The statemachine-engine was extracted from the face-changer project. The protocol layer (Unix sockets) is clean, but **semantic residue** remains:

| Location | Remnant | Type |
|----------|---------|------|
| `database/models/__init__.py:4` | "extracted from face-changer project" | Doc comment |
| `database/models/__init__.py:23` | "legacy singleton" pattern | Architecture smell |
| `database/models/base.py:59` | "domain-specific tables (face-changer)" | Dead code comment |
| `check_database_queue_action.py:33` | `face_processing` as default job_type | Logic leak |
| `check_database_queue_action.py:6,27` | "pony_flux" job type references | Domain coupling |
| `engine.py:14` | References to `face_changer.yaml` in docstring | Stale doc |
| `bash_action.py:13` | References `face_changer_database.yaml` in docstring | Stale doc |
| `core/action_loader.py:68` | "legacy names" alias comment | Minor |
| `tools/cli.py:59`, `diagrams.py:933` | "legacy positional arg" | CLI compat note |

## Proposed Solution

### Phase 1: Remove stale references

1. **Update docstrings** — Remove references to `face_changer.yaml`, `face_changer_database.yaml`
2. **Update comments** — Remove "extracted from face-changer" and "domain-specific tables (face-changer)"
3. **Clean job_type default** — Change `face_processing` default to `None` (require explicit config)

### Phase 2: Neutralize domain coupling

```python
# Before (check_database_queue_action.py)
self.job_type = config.get("job_type", "face_processing")

# After
self.job_type = config.get("job_type")
if not self.job_type:
    raise ValueError("job_type is required in check_database_queue config")
```

### Phase 3: Document legacy patterns

Add a note in CLAUDE.md under "Historical Context" explaining:
- Origin as face-changer extraction
- Status of genericization
- Remaining legacy patterns (action aliases, CLI positional args)

## Acceptance Criteria

- [ ] No references to `face_changer`, `face-changer`, `face_processing`, or `pony_flux` in source code
- [ ] `job_type` requires explicit configuration (no hidden defaults)
- [ ] Stale docstrings updated with generic examples
- [ ] Historical context documented in CLAUDE.md
- [ ] Tests pass (may need fixture updates for job_type)

## Alternatives Considered

1. **Keep as-is** — Minimal disruption, but confuses new users
2. **Full refactor** — Too expensive for cosmetic cleanup
3. **Just update docs** — Leaves logic leaks in place

## Related

- FSM Unix socket migration (completed)
- `node_modules` in `ui/` (separate cleanup issue — not part of this FR)
