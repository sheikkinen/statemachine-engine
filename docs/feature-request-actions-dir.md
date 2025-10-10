# Feature Request: Custom Actions Directory Parameter

## User Story

**As a** state machine developer building custom workflows

**I want** to specify a custom actions directory via CLI parameter

**So that** I can use project-specific custom actions without installing my project as a Python package

## Background

Currently, the `ActionLoader` discovers actions only from the installed `statemachine_engine` package's `actions/` directory. For developers working on custom state machine projects (e.g., `sdxl_generator`, `face_changer`), this creates friction:

- **Current workaround**: Must install project as package (`pip install -e .`) to make actions discoverable
- **Problem**: Heavy overhead for simple projects that just need a few custom actions
- **Impact**: Slows down development iteration and adds complexity to project setup

## Proposed Solution

Add `--actions-dir` CLI parameter to the `statemachine` command:

```bash
statemachine config/worker.yaml \
  --machine-name my_worker \
  --actions-dir ./my_project/actions
```

## Acceptance Criteria

### Must Have

- [ ] CLI accepts `--actions-dir` parameter with absolute or relative path
- [ ] `ActionLoader` is initialized with custom `actions_root` when parameter provided
- [ ] Custom actions are discovered using existing naming convention (`{action_type}_action.py` → `{ActionType}Action`)
- [ ] Falls back to default behavior (package actions) when parameter not provided
- [ ] Error handling for invalid or non-existent paths
- [ ] Documentation updated with usage examples

### Should Have

- [ ] Supports both absolute and relative paths (relative to current working directory)
- [ ] Clear error messages when action directory doesn't exist or contains invalid actions
- [ ] Works seamlessly with existing built-in actions (custom actions can supplement built-ins)

### Nice to Have

- [ ] Support multiple action directories via comma-separated paths or repeated parameter
- [ ] Environment variable alternative (e.g., `STATEMACHINE_ACTIONS_DIR`)
- [ ] Validation that prints discovered actions when using custom directory (with `--debug` flag)

## Technical Implementation Notes

The groundwork already exists in `ActionLoader`:

```python
class ActionLoader:
    def __init__(self, actions_root: str = None):
        if actions_root is None:
            # Auto-detect: src/actions relative to this file
            this_file = Path(__file__)
            actions_root = str(this_file.parent.parent / 'actions')
        
        self.actions_root = Path(actions_root)
        # ... discovery logic
```

**Required Changes:**

1. **CLI Argument Parsing** (`src/cli.py` or equivalent):
   ```python
   parser.add_argument(
       '--actions-dir',
       type=str,
       help='Path to custom actions directory'
   )
   ```

2. **Engine Initialization**:
   ```python
   # Pass actions_root to ActionLoader
   if args.actions_dir:
       actions_path = Path(args.actions_dir).resolve()
       if not actions_path.exists():
           raise ValueError(f"Actions directory not found: {actions_path}")
       loader = ActionLoader(actions_root=str(actions_path))
   else:
       loader = ActionLoader()  # Use default
   ```

3. **Path Resolution**:
   - Convert relative paths to absolute based on current working directory
   - Validate path exists and is a directory
   - Handle `~` (home directory) expansion

## Use Cases

### Use Case 1: SDXL Generator Development

```bash
# Developer working on SDXL generator with custom LangChain actions
cd /path/to/image-generator-fsm
statemachine sdxl_generator/config/sdxl_generator.yaml \
  --machine-name sdxl_generator \
  --actions-dir sdxl_generator/actions
```

**Custom actions:**
- `enhance_prompt_action.py` - LangChain prompt enhancement
- `update_job_prompt_action.py` - Database updates
- `create_face_job_action.py` - Job queue management

### Use Case 2: Multi-Project Workspace

```bash
# Shared actions directory for multiple related projects
statemachine projects/worker1/config.yaml \
  --machine-name worker1 \
  --actions-dir shared/actions

statemachine projects/worker2/config.yaml \
  --machine-name worker2 \
  --actions-dir shared/actions
```

### Use Case 3: Testing and CI/CD

```bash
# Test with mock actions directory
statemachine config/worker.yaml \
  --machine-name test_worker \
  --actions-dir tests/mock_actions
```

## Benefits

1. **Developer Experience**: No package installation required for custom actions
2. **Project Organization**: Actions live alongside configs where they logically belong
3. **Iteration Speed**: Edit action → test immediately (no reinstall)
4. **CI/CD Friendly**: Simple directory structure without package metadata
5. **Clear and Explicit**: No PYTHONPATH manipulation or import magic needed
6. **Backward Compatible**: Existing projects work without changes

## Comparison: Current vs. Proposed

### Current Workflow (Package Installation Required)

```bash
# Setup overhead
cat > setup.py << 'EOF'
from setuptools import setup, find_packages
setup(
    name='sdxl_generator',
    version='0.1.0',
    packages=find_packages(),
)
EOF

pip install -e .

# Now can run
statemachine sdxl_generator/config/sdxl_generator.yaml --machine-name sdxl_generator
```

### Proposed Workflow (Direct Actions Directory)

```bash
# No setup needed, just run
statemachine sdxl_generator/config/sdxl_generator.yaml \
  --machine-name sdxl_generator \
  --actions-dir sdxl_generator/actions
```

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Path resolution confusion | Medium | Always resolve to absolute paths; document behavior clearly |
| Action naming conflicts | Low | Custom actions override built-ins (document precedence) |
| Import path issues | Medium | Validate directory structure; clear error messages |
| Performance impact | Low | Action discovery happens once at startup |

## References

- `ActionLoader` implementation: `src/core/action_loader.py`
- Current documentation: `docs-engine/README.md` (Custom Actions section)
- Example projects affected: `sdxl_generator/`, `face_changer/`, `controller/`

## Success Metrics

- **Developer Time Saved**: Eliminate ~5 minutes of package setup per project
- **Adoption**: 80%+ of custom action projects use `--actions-dir` instead of package installation
- **Documentation**: Zero confusion issues reported in first month after release
- **Backward Compatibility**: 100% of existing projects continue working without changes

## Priority

**HIGH** - This feature significantly improves developer experience and removes a common friction point for custom action development.

## Estimated Effort

- **Implementation**: 2-4 hours (CLI argument, path resolution, testing)
- **Documentation**: 1 hour (README updates, examples)
- **Testing**: 2 hours (unit tests, integration tests, edge cases)

**Total**: ~1 day

---

*Created*: October 10, 2025  
*Status*: Proposed  
*Target Version*: 1.1.0
