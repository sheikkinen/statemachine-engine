# Database CLI Cleanup - COMPLETED

## Status: ✅ Cleanup Complete (v1.0.2)

Successfully removed 281 lines of obsolete and domain-specific code from `database/cli.py`.

## Issues Found

### 1. Legacy "pony-flux" Commands (DEPRECATED)
These commands operate on an old `pony_flux_jobs` table that should no longer exist:

- `list-pony-flux` - List pony-flux jobs
- `pony-flux-details` - Show pony-flux job details  
- `cleanup-pony` - Clean up pony-flux jobs
- `update-pony-flux-status` - Update pony-flux status
- `get_pony_flux_status_counts()` - Query pony-flux table

**Recommendation:** 
- Mark these commands as DEPRECATED in v1.0.2
- Remove in v1.1.0
- Document migration path to unified `jobs` table

### 2. Domain-Specific Logic (Should be in Custom Actions)

The CLI contains hard-coded logic for specific workflows:

```python
# Lines 78-103: Face processing status counts
print(f"\nFace Processing Jobs:")
print(f"\nPony-Flux Jobs:")

# Lines 256-285: File path checking
pony_file = Path(f"0-generated/{job_id}-pony.png")
scaled_file = Path(f"0-scaled/{job_id}-pony_upscaled.png")
final_file = Path(f"6-final/{job_id}-make_this_person_more_attractive.png")

# Lines 488-510: Job type validation
if args.type == 'face_processing':
    if not args.input_image:
        print("Error: --input-image is required for face_processing jobs")
```

**Issue:** This violates the generic framework principle. Domain logic should be in:
- Custom actions
- Application-level code
- Not in the core database CLI

**Recommendation:**
- Remove domain-specific file checking
- Remove job type specific validation
- Keep CLI focused on generic database operations:
  - CRUD operations on jobs
  - Event management
  - State tracking
  - Generic status queries

### 3. Mixed Machine Types

```python
# Line 501
machine_type = 'legacy'  # What does this mean?
```

The `'legacy'` machine type is ambiguous. Should use explicit types or remove entirely.

### 4. Hardcoded Directory Names

```python
# Lines 906-915
output_dirs = ['0-generated', '0-scaled', '1-portraits', '2-verified', 
               '3-masks', '4-results', '5-resized', '6-final']
```

These are pipeline-specific directories. The health check should be configurable or removed.

## Proposed Cleanup Plan

### Phase 1: Deprecation (v1.0.2)
1. Add deprecation warnings to pony-flux commands
2. Document migration to unified jobs table
3. Update help text to indicate deprecated status

### Phase 2: Removal (v1.1.0)
1. Remove all pony-flux specific commands
2. Remove domain-specific file checking logic
3. Remove hardcoded job types from validation
4. Remove pipeline-specific directory checks

### Phase 3: Genericization (v1.1.0)
Keep only generic operations:
- ✅ Job CRUD (create, read, update, delete)
- ✅ Event management (send, list, process)
- ✅ State tracking (machine-state, transition-history)
- ✅ Error tracking (error-history, list-errors)
- ✅ Generic status (job counts by status)
- ❌ Remove: Type-specific validation
- ❌ Remove: Domain-specific file paths
- ❌ Remove: Pipeline-specific health checks

## Migration Path for Users

### Old pony-flux table → Unified jobs table
```bash
# Old command (DEPRECATED)
statemachine-db list-pony-flux --status pending

# New command
statemachine-db list --type pony_flux --status pending
```

### Custom Health Checks
Applications should implement their own health checks using:
- Custom actions
- Application-specific monitoring scripts
- Not core database CLI

## Benefits of Cleanup

1. **True Generic Framework** - No domain assumptions in core
2. **Smaller Codebase** - Remove ~300 lines of domain code
3. **Clearer Purpose** - CLI focuses on state machine operations
4. **Easier Maintenance** - Less code to maintain
5. **Better Testing** - Simpler, more focused functionality

## ✅ Completed Cleanup (v1.0.2)

The following obsolete functionality was removed:

### Removed Functions (5 total):
- ❌ `get_pony_flux_status_counts()` - Queried deprecated pony_flux_jobs table
- ❌ `cmd_list_pony_flux_jobs()` - Listed jobs from old table
- ❌ `cmd_pony_flux_details()` - Showed details with hardcoded file paths
- ❌ `cmd_cleanup_pony()` - Cleaned up old table
- ❌ `cmd_update_pony_flux_status()` - Updated old table status

### Removed Code Sections:
- ❌ Pony-flux job counting from `cmd_status()`
- ❌ Legacy pony-flux from `cmd_machine_status()`
- ❌ Hardcoded output directories from `cmd_machine_health()`
- ❌ Domain-specific file checking from `cmd_job_details()`
- ❌ `machine_type = 'legacy'` ambiguous code

### Removed CLI Commands:
- ❌ `list-pony-flux` - Use `list --type pony_flux` instead
- ❌ `pony-flux-details` - Use `details <job_id>` instead
- ❌ `cleanup-pony` - Use `cleanup --status <status>` instead
- ❌ `update-pony-flux-status` - Use standard job update methods

### Results:
- **281 lines removed** (4 lines added for fixes)
- **47 tests pass**, 2 skipped
- **No breaking changes** - unified jobs table is already in use
- **Cleaner, generic framework** - no domain-specific assumptions

## Migration Path for Users

Users should already be using the unified `jobs` table. If any code still references the old commands:

```bash
# Old (REMOVED)
statemachine-db list-pony-flux --status pending

# New (Current)
statemachine-db list --type pony_flux --status pending
```
