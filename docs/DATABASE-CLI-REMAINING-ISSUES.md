# Additional Deprecated/Domain-Specific Code in Database CLI

## Issues Found (After Initial Cleanup)

### 1. **Module Docstring** - Lines 1-7
```python
"""
Database CLI for face-changer pipeline
```
❌ **Problem**: References specific "face-changer pipeline" - not generic

### 2. **ArgumentParser Description** - Line 1107
```python
parser = argparse.ArgumentParser(description="Database CLI for face-changer pipeline")
```
❌ **Problem**: Same domain-specific description

### 3. **cmd_status() - Domain-Specific Job Counts** - Lines 63-73
```python
print(f"\nFace Processing Jobs:")
fp_total = job_model.count_jobs(job_type='face_processing')
fp_pending = job_model.count_jobs('pending', 'face_processing')
# ... etc
```
❌ **Problem**: Hardcoded face_processing job type counting

### 4. **cmd_machine_status() - Domain-Specific Job Types** - Lines 605-617
```python
face_pending = len(job_model.list_jobs(job_type='face_processing', status='pending'))
# ... Face Processing, SDXL Generation, etc.
print(f"  Face Processing: {face_pending} pending...")
print(f"  SDXL Generation: {sdxl_pending} pending...")
```
❌ **Problem**: Hardcoded domain-specific job types

### 5. **cmd_add_job() - Domain-Specific Validation** - Lines 284-302
```python
if args.type == 'face_processing':
    if not args.input_image:
        print("Error: --input-image is required for face_processing jobs")
        return 1
elif args.type in ['pony_flux', 'sdxl_generation']:
    if not args.pony_prompt or not args.flux_prompt:
        print(f"Error: --pony-prompt and --flux-prompt are required for {args.type} jobs")
# ... etc
if args.type == 'sdxl_generation':
    machine_type = 'sdxl_generator'
elif args.type == 'face_processing':
    machine_type = 'face_processor'
else:
    machine_type = args.type
```
❌ **Problem**: Domain-specific validation logic, hardcoded machine types

### 6. **cmd_add_job() - Domain-Specific Arguments** - Lines 1147-1156
```python
--type {face_processing,pony_flux,sdxl_generation}
--input-image (for face_processing)
--prompt "AI prompt for face modification"
--pony-prompt "Pony model prompt"
--flux-prompt "Flux model prompt"
--padding-factor "Face crop padding factor"
--mask-padding-factor "Mask padding factor"
```
❌ **Problem**: All of these are domain-specific to face processing pipelines

### 7. **cmd_migrate_queue() - Deprecated Feature** - Lines 144-180
```python
def cmd_migrate_queue(args):
    """Migrate existing queue.json to database"""
```
❌ **Problem**: Legacy migration from old queue.json format - likely obsolete

### 8. **cmd_job_details() - Domain-Specific Display** - Lines 100-115
```python
if job['job_type'] in ['sdxl_generation', 'pony_flux']:
    print(f"  Pony Prompt: {data.get('pony_prompt', 'N/A')}")
    print(f"  Flux Prompt: {data.get('flux_prompt', 'N/A')}")
else:
    print(f"  Image: {data.get('input_image_path', 'N/A')}")
    print(f"  Prompt: {data.get('user_prompt', 'N/A')}")

print(f"  Padding Factor: {data.get('padding_factor', 1.5)}")
print(f"  Mask Padding: {data.get('mask_padding_factor', 1.2)}")
```
❌ **Problem**: Domain-specific field display logic

### 9. **cmd_list_jobs() - Domain-Specific Display** - Lines 86-96
```python
if args.type == 'pony_flux':
    headers = ['ID', 'Type', 'Status', 'Created', 'Pony Prompt', 'Flux Prompt']
    # ... pony/flux specific columns
else:
    headers = ['ID', 'Type', 'Status', 'Created', 'Image', 'Prompt']
    # ... image/prompt specific columns
```
❌ **Problem**: Domain-specific table formatting

### 10. **get_pipeline_model() Import** - Used in cmd_job_details
```python
pipeline_model = get_pipeline_model()
results = pipeline_model.get_job_results(args.job_id)
```
❌ **Problem**: References pipeline-specific results (face processing steps)

## Recommendation

These commands are **highly domain-specific** to a face-processing/image-generation pipeline. Options:

### Option A: Remove Completely (Best for Generic Framework)
- Remove domain-specific commands: `add-job` (with domain validation), `migrate`
- Keep only: CRUD operations, event management, state tracking
- Remove domain-specific counting from `status` and `machine-status`

### Option B: Make Generic
- Remove job type enums - allow any string
- Remove validation logic - let applications validate
- Remove domain-specific display formatting
- Generic field display (JSON or key-value pairs)

### Option C: Extract to Application Layer
- Move domain-specific commands to application-level CLI
- Keep generic database operations in core
- Create example CLI in `examples/` for reference

## Priority

**CRITICAL**: This violates the generic framework principle severely
- The CLI is tightly coupled to a specific application domain
- Should be cleaned up before claiming "generic framework"
