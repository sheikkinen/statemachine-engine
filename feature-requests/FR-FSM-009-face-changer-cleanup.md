# Feature Request: Face-Changer Remnant Cleanup

**Priority:** MEDIUM
**Type:** Enhancement
**Status:** Proposed
**Effort:** 1 day
**Requested:** 2026-03-14

## Summary

Remove face-changer domain-specific logic and references from the genericized statemachine-engine codebase.

## Value Statement

New users of the generic FSM engine get a clean codebase without confusing references to an obsolete domain (face-changer), reducing onboarding friction and eliminating dead code paths.

## Problem

The statemachine-engine was extracted from the face-changer project. The protocol layer (Unix sockets) is clean, but **semantic residue** and **domain-specific logic** remain:

### Stale Documentation

| Location | Remnant | Type |
|----------|---------|------|
| `database/models/__init__.py:4` | "extracted from face-changer project" | Doc comment |
| `database/models/__init__.py:23` | "legacy singleton" pattern | Architecture smell |
| `database/models/base.py:59` | "domain-specific tables (face-changer)" | Dead code comment |
| `engine.py:14` | References to `face_changer.yaml` in docstring | Stale doc |
| `bash_action.py:13` | References `face_changer_database.yaml` in docstring | Stale doc |
| `core/action_loader.py:68` | "legacy names" alias comment | Minor |
| `tools/cli.py:59`, `diagrams.py:933` | "legacy positional arg" | CLI compat note |

### Domain-Specific Logic (More Serious)

| Location | Code | Impact |
|----------|------|--------|
| `job.py:47` | Example uses `input_image_path` | Misleading docstring |
| `job.py:424-457` | `get_processing_jobs_with_missing_files()` | Hardcodes check for `input_image_path` field |
| `job.py:460-475` | `store_pipeline_result()` | **Dead code** — `pipeline_results` table doesn't exist |
| `check_database_queue_action.py:6,27` | "face_processing and pony_flux" | Domain-specific docstring |
| `check_database_queue_action.py:33` | `job_type` defaults to `"face_processing"` | Hidden coupling |
| `check_database_queue_action.py:41-42` | Conditional `if self.job_type == "face_processing"` | Domain logic in generic action |
| `check_database_queue_action.py:84-106` | `_fail_jobs_with_missing_files()` | Face-changer specific cleanup |
| `bash_action.py:9,22-24,47` | `no_faces_detected` in docstrings and examples | Domain-specific error |
| `bash_action.py:312` | `if mapped_error in ["no_faces_detected"]` | **Hardcoded special case** |

### Phantom Table

The `pipeline_results` table is referenced in 3 files but **never created in schema**:
- `job.py:467` — INSERT
- `machine_state.py:77,86` — SELECT
- `check_machine_state_action.py:114,122` — SELECT

## Proposed Solution

### Phase 1: Remove dead code

1. **Remove** `get_processing_jobs_with_missing_files()` from `job.py` — domain-specific, belongs in custom action
2. **Remove** `store_pipeline_result()` from `job.py` — dead code, `pipeline_results` table doesn't exist
3. **Remove** `_fail_jobs_with_missing_files()` from `check_database_queue_action.py`
4. **Remove** hardcoded `["no_faces_detected"]` special case from `bash_action.py:312`

### Phase 2: Neutralize domain coupling

```python
# Before (check_database_queue_action.py)
self.job_type = config.get("job_type", "face_processing")

# After
self.job_type = config.get("job_type")
if not self.job_type:
    raise ValueError("job_type is required in check_database_queue config")
```

Remove conditional `if self.job_type == "face_processing"` logic — validation should be generic or configurable.

### Phase 3: Clean documentation

1. **Update docstrings** — Remove references to `face_changer.yaml`, `face_changer_database.yaml`, `input_image_path`
2. **Update comments** — Remove "extracted from face-changer" and "domain-specific tables (face-changer)"
3. **Update examples** — Replace `no_faces_detected` with generic error mapping examples

### Phase 4: Document legacy patterns

Add a note in CLAUDE.md under "Historical Context" explaining:
- Origin as face-changer extraction
- Status of genericization
- Remaining legacy patterns (action aliases, CLI positional args)

## Acceptance Criteria

- [ ] No references to `face_changer`, `face-changer`, `face_processing`, `pony_flux`, `no_faces_detected`, or `input_image_path` in source code
- [ ] `get_processing_jobs_with_missing_files()` removed from `job.py`
- [ ] `store_pipeline_result()` removed from `job.py`
- [ ] `_fail_jobs_with_missing_files()` removed from `check_database_queue_action.py`
- [ ] Hardcoded `["no_faces_detected"]` removed from `bash_action.py`
- [ ] `job_type` requires explicit configuration (no hidden defaults)
- [ ] Stale docstrings updated with generic examples
- [ ] Historical context documented in CLAUDE.md
- [ ] Tests pass (may need fixture updates for job_type and removed methods)

## Alternatives Considered

1. **Keep as-is** — Minimal disruption, but confuses new users
2. **Full refactor** — Too expensive for cosmetic cleanup
3. **Just update docs** — Leaves logic leaks in place

## Related

- FSM Unix socket migration (completed)
- `node_modules` in `ui/` (separate cleanup issue — not part of this FR)
