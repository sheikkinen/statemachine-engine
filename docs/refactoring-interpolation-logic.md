# Variable Interpolation Logic Refactoring Plan

**Date**: 2025-11-10  
**Status**: Planning  
**Priority**: HIGH  
**Approach**: TDD (Test-Driven Development)

---

## Executive Summary

Variable interpolation (`{variable}` substitution) is currently duplicated in **at least 3 locations** with inconsistent implementations. This refactoring will:

1. Extract a single, well-tested utility module
2. Use engine's implementation as the master reference (most feature-complete)
3. Write comprehensive tests first (TDD)
4. Migrate all usages to the shared module
5. Remove duplicate implementations

**Estimated Effort**: 3-4 hours  
**Risk Level**: LOW (pure refactor with existing test coverage)

---

## Current State Analysis

### Duplicate Implementations Found

#### 1. **Engine** (`core/engine.py`) - MASTER IMPLEMENTATION ✅

**Location**: Lines 637-683  
**Methods**: 
- `_substitute_variables(template, context)` - Main substitution
- `_interpolate_config(config, context)` - Recursive dict/list processing

**Features**:
- ✅ Simple variables: `{job_id}`, `{status}`
- ✅ Nested dot notation: `{event_data.payload.job_id}`
- ✅ Preserves unknown placeholders (no crash)
- ✅ Type safety (handles non-string templates)
- ✅ Recursive dict/list processing
- ✅ **15 comprehensive tests** in `tests/core/test_engine_interpolation.py`

**Pattern**:
```python
def _substitute_variables(self, template: str, context: Dict[str, Any]) -> str:
    """Substitute {variable} placeholders with context values.
    
    Supports:
    - Simple variables: {job_id}, {id}, {status}
    - Nested keys with dot notation: {event_data.payload.job_id}
    - Leaves unknown placeholders unchanged
    """
    import re
    
    if not isinstance(template, str):
        return template
        
    pattern = r'\{([a-zA-Z_][a-zA-Z0-9_.]*)\}'
    
    def replace_match(match):
        key = match.group(1)
        
        # Handle nested keys (e.g., event_data.payload.job_id)
        if '.' in key:
            parts = key.split('.')
            obj = context
            for part in parts:
                if isinstance(obj, dict):
                    obj = obj.get(part)
                    if obj is None:
                        return match.group(0)  # Keep placeholder
                else:
                    return match.group(0)  # Keep placeholder
            return str(obj) if obj is not None else match.group(0)
        
        # Handle simple keys
        value = context.get(key)
        if value is not None:
            return str(value)
        
        return match.group(0)  # Keep placeholder if not found
    
    return re.sub(pattern, replace_match, template)
```

---

#### 2. **CompleteJobAction** (`actions/builtin/complete_job_action.py`)

**Location**: Lines 68-78  
**Method**: `_interpolate_variables(template, context)`

**Features**:
- ✅ Simple variables only: `{job_id}`
- ❌ NO nested dot notation support
- ✅ Preserves unknown placeholders
- ✅ **3 tests** in `tests/actions/test_complete_job_action.py`

**Pattern**:
```python
def _interpolate_variables(self, template: str, context: Dict[str, Any]) -> str:
    """Replace {var} placeholders with context values"""
    import re
    
    def replace_var(match):
        var_name = match.group(1)
        value = context.get(var_name)
        return str(value) if value is not None else match.group(0)
    
    return re.sub(r'\{(\w+)\}', replace_var, template)
```

**Issues**:
- Simpler regex pattern: `\{(\w+)\}` - doesn't handle dots
- No type safety check
- Less robust than engine version

---

#### 3. **StartFSMAction** (`actions/builtin/start_fsm_action.py`)

**Location**: Lines 224-267  
**Method**: `_interpolate_variables(template, context)`

**Features**:
- ✅ Simple variables: `{job_id}`
- ✅ Nested dot notation: `{current_job.id}`
- ✅ Preserves unknown placeholders
- ⚠️ Different implementation (manual string replacement, not regex)
- ✅ **15 tests** in `tests/actions/test_start_fsm_action.py`

**Pattern**:
```python
def _interpolate_variables(self, template: str, context: Dict[str, Any]) -> str:
    """
    Replace {variable} placeholders with values from context.
    
    Supports simple and nested variable substitution:
    - {job_id} -> context['job_id']
    - {current_job.id} -> context['current_job']['id']
    """
    result = template
    
    # Find all {variable} and {nested.variable} patterns
    pattern = r'\{([\w\.]+)\}'
    matches = re.findall(pattern, template)
    
    # Replace each variable
    for var_path in matches:
        # Handle nested paths like current_job.id
        if '.' in var_path:
            parts = var_path.split('.')
            value = context
            try:
                for part in parts:
                    value = value[part]
                result = result.replace(f'{{{var_path}}}', str(value))
            except (KeyError, TypeError):
                logger.warning(f"StartFsmAction: Nested variable '{var_path}' not found in context")
        # Handle simple variables
        else:
            if var_path in context:
                result = result.replace(f'{{{var_path}}}', str(context[var_path]))
            else:
                logger.warning(f"StartFsmAction: Variable '{var_path}' not found in context")
    
    return result
```

**Issues**:
- Uses `string.replace()` instead of regex substitution
- Could cause double-replacement bugs with overlapping placeholders
- Logs warnings (engine version is silent)

---

#### 4. **BashAction** (`actions/builtin/bash_action.py`)

**Location**: Lines 75-160 (inline, not a method)  
**Method**: Inline string replacement logic

**Features**:
- ✅ Special handling for quoted placeholders: `"{prompt}"`, `"{output}"`
- ✅ Fallback syntax: `"{prompt:-pony_prompt}"`
- ❌ NO method extraction (embedded in execute())
- ✅ **15 tests** in `tests/actions/test_bash_action_*.py`

**Pattern**:
```python
# Inline replacement logic embedded in execute() method
# Different from other actions - handles shell escaping
command = self.config.get('command')

# Special handling for quoted placeholders
if '"{prompt}"' in command or '"{output}"' in command:
    # Replace with escaped values
    command = command.replace('"{prompt}"', f'"{escaped_prompt}"')
```

**Issues**:
- Not extracted to reusable method
- Bash-specific (shell escaping), not general-purpose
- Should stay unique to BashAction (not part of refactor)

---

#### 5. **SendEventAction** (`actions/builtin/send_event_action.py`)

**Location**: Line 196-200 (partial inline)  
**Method**: Inline `string.replace()` for specific case

**Pattern**:
```python
# Inline replacement for {id} only
if isinstance(extracted_value, str) and '{id}' in extracted_value:
    substitute_id = event_job_id or job_id
    extracted_value = extracted_value.replace('{id}', substitute_id if substitute_id else '{id}')
```

**Issues**:
- Only handles `{id}` placeholder
- Inline, not extracted to method
- Should use general interpolation utility after refactor

---

### Summary of Duplicates

| Location | Lines | Features | Tests | Status |
|----------|-------|----------|-------|--------|
| **Engine** (MASTER) | 637-703 | Simple + Nested + Recursive | 15 | ✅ Keep as reference |
| CompleteJobAction | 68-78 | Simple only | 3 | ❌ Remove (migrate) |
| StartFSMAction | 224-267 | Simple + Nested (different impl) | 15 | ❌ Remove (migrate) |
| BashAction | 75-160 | Bash-specific escaping | 15 | ✅ Keep (unique logic) |
| SendEventAction | 196-200 | Inline {id} only | 0 | ❌ Remove (migrate) |

**Total Duplication**: ~80 lines across 3 files (excluding BashAction which is unique)

---

## Target Architecture

### New Module: `statemachine_engine/utils/interpolation.py`

```
src/
  statemachine_engine/
    utils/
      __init__.py           # NEW
      interpolation.py      # NEW - extracted utility
    core/
      engine.py             # REMOVE duplicate, import from utils
    actions/
      builtin/
        complete_job_action.py   # REMOVE duplicate, import from utils
        start_fsm_action.py      # REMOVE duplicate, import from utils
        send_event_action.py     # REFACTOR inline usage
```

### Public API

```python
# statemachine_engine/utils/interpolation.py

from typing import Dict, Any

def interpolate_string(template: str, context: Dict[str, Any]) -> str:
    """
    Replace {variable} placeholders with context values.
    
    Supports:
    - Simple variables: {job_id}, {status}
    - Nested dot notation: {event_data.payload.job_id}
    - Preserves unknown placeholders unchanged
    
    Args:
        template: String with {variable} placeholders
        context: Dictionary with variable values
    
    Returns:
        String with variables replaced
    
    Examples:
        >>> interpolate_string("Job {job_id}", {"job_id": "123"})
        'Job 123'
        
        >>> interpolate_string("Status: {payload.status}", {"payload": {"status": "done"}})
        'Status: done'
        
        >>> interpolate_string("Unknown {missing}", {})
        'Unknown {missing}'
    """
    pass  # Implementation copied from engine._substitute_variables


def interpolate_dict(config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively interpolate variables in dict/list structures.
    
    Processes all string values, replacing {variable} placeholders.
    Handles nested dicts and lists recursively.
    
    Args:
        config: Dictionary or list with string values to interpolate
        context: Dictionary with variable values
    
    Returns:
        New dict/list with variables replaced
    
    Examples:
        >>> interpolate_dict({"msg": "Job {id}"}, {"id": "123"})
        {'msg': 'Job 123'}
        
        >>> interpolate_dict({"cmd": ["run", "{file}"]}, {"file": "test.py"})
        {'cmd': ['run', 'test.py']}
    """
    pass  # Implementation copied from engine._interpolate_config
```

---

## TDD Implementation Plan

### Phase 1: Write Tests First (1 hour)

#### Step 1.1: Create Test File

**File**: `tests/utils/test_interpolation.py`

**Test Coverage** (copy/adapt from existing engine tests):

```python
import pytest
from statemachine_engine.utils.interpolation import interpolate_string, interpolate_dict

class TestInterpolateString:
    """Test simple string interpolation"""
    
    def test_simple_variable(self):
        """Replace {job_id} with context value"""
        result = interpolate_string("Job {job_id}", {"job_id": "123"})
        assert result == "Job 123"
    
    def test_nested_variable(self):
        """Replace {event_data.payload.status} with nested value"""
        context = {
            "event_data": {
                "payload": {"status": "completed"}
            }
        }
        result = interpolate_string("Status: {event_data.payload.status}", context)
        assert result == "Status: completed"
    
    def test_missing_variable_preserved(self):
        """Keep {unknown} unchanged when not in context"""
        result = interpolate_string("Value: {unknown}", {})
        assert result == "Value: {unknown}"
    
    def test_multiple_variables(self):
        """Replace multiple variables in one string"""
        context = {"job_id": "123", "status": "done"}
        result = interpolate_string("Job {job_id}: {status}", context)
        assert result == "Job 123: done"
    
    def test_non_string_template(self):
        """Return non-strings unchanged"""
        assert interpolate_string(123, {}) == 123
        assert interpolate_string(None, {}) is None
    
    def test_special_characters_in_value(self):
        """Handle special chars in values"""
        context = {"msg": "Hello! @#$%"}
        result = interpolate_string("Message: {msg}", context)
        assert result == "Message: Hello! @#$%"
    
    def test_numeric_value_conversion(self):
        """Convert numeric values to strings"""
        context = {"count": 42, "price": 99.99}
        result = interpolate_string("Count: {count}, Price: {price}", context)
        assert result == "Count: 42, Price: 99.99"
    
    def test_braces_in_non_variable_context(self):
        """Preserve braces that aren't variables"""
        result = interpolate_string("Set: {{1, 2, 3}}", {})
        assert result == "Set: {{1, 2, 3}}"
    
    def test_deeply_nested_variable(self):
        """Handle deeply nested paths"""
        context = {
            "a": {"b": {"c": {"d": "value"}}}
        }
        result = interpolate_string("Deep: {a.b.c.d}", context)
        assert result == "Deep: value"
    
    def test_nested_missing_intermediate(self):
        """Keep placeholder when intermediate key missing"""
        context = {"a": {"b": "value"}}
        result = interpolate_string("Path: {a.missing.c}", context)
        assert result == "Path: {a.missing.c}"


class TestInterpolateDict:
    """Test recursive dict/list interpolation"""
    
    def test_simple_dict(self):
        """Interpolate string values in dict"""
        config = {"message": "Job {job_id}"}
        context = {"job_id": "123"}
        result = interpolate_dict(config, context)
        assert result == {"message": "Job 123"}
    
    def test_nested_dict(self):
        """Recursively interpolate nested dicts"""
        config = {
            "action": {
                "type": "log",
                "message": "Processing {job_id}"
            }
        }
        context = {"job_id": "456"}
        result = interpolate_dict(config, context)
        assert result["action"]["message"] == "Processing 456"
    
    def test_list_values(self):
        """Interpolate strings in lists"""
        config = {
            "commands": ["run {file}", "output {dir}"]
        }
        context = {"file": "test.py", "dir": "/tmp"}
        result = interpolate_dict(config, context)
        assert result["commands"] == ["run test.py", "output /tmp"]
    
    def test_mixed_types(self):
        """Preserve non-string types"""
        config = {
            "str": "Job {id}",
            "int": 42,
            "bool": True,
            "none": None
        }
        context = {"id": "789"}
        result = interpolate_dict(config, context)
        assert result["str"] == "Job 789"
        assert result["int"] == 42
        assert result["bool"] is True
        assert result["none"] is None
    
    def test_deeply_nested_structure(self):
        """Handle complex nested structures"""
        config = {
            "level1": {
                "level2": {
                    "commands": ["cmd {var1}", "cmd {var2}"],
                    "message": "Status: {status}"
                }
            }
        }
        context = {"var1": "A", "var2": "B", "status": "OK"}
        result = interpolate_dict(config, context)
        assert result["level1"]["level2"]["commands"] == ["cmd A", "cmd B"]
        assert result["level1"]["level2"]["message"] == "Status: OK"


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_context(self):
        """Handle empty context gracefully"""
        result = interpolate_string("Value: {x}", {})
        assert result == "Value: {x}"
    
    def test_empty_template(self):
        """Handle empty string"""
        result = interpolate_string("", {"x": "y"})
        assert result == ""
    
    def test_none_value_in_context(self):
        """Skip None values (keep placeholder)"""
        result = interpolate_string("Value: {x}", {"x": None})
        assert result == "Value: {x}"
    
    def test_circular_reference_protection(self):
        """Don't infinite loop on self-referential context"""
        circular = {"a": "value"}
        circular["self"] = circular  # Create circular reference
        result = interpolate_string("Value: {a}", circular)
        assert result == "Value: value"
```

**Total Tests**: 25+ comprehensive tests

---

### Phase 2: Implement Utility Module (1 hour)

#### Step 2.1: Create Module Structure

```bash
# Create directory and files
mkdir -p src/statemachine_engine/utils
touch src/statemachine_engine/utils/__init__.py
touch src/statemachine_engine/utils/interpolation.py
mkdir -p tests/utils
touch tests/utils/__init__.py
touch tests/utils/test_interpolation.py
```

#### Step 2.2: Implement `interpolation.py`

**Copy from engine.py** (lines 637-703):
- `_substitute_variables` → `interpolate_string`
- `_interpolate_config` → `interpolate_dict`

**Add docstrings and type hints** (see Public API section above)

#### Step 2.3: Run Tests

```bash
# Run new tests - should PASS
pytest tests/utils/test_interpolation.py -v

# Run all tests - should PASS (no changes yet)
pytest tests/ -v
```

---

### Phase 3: Migrate Engine (30 min)

#### Step 3.1: Update Engine to Use Utility

**File**: `src/statemachine_engine/core/engine.py`

```python
# ADD import at top
from ..utils.interpolation import interpolate_string, interpolate_dict

class StateMachineEngine:
    # ... existing code ...
    
    def _substitute_variables(self, template: str, context: Dict[str, Any]) -> str:
        """DEPRECATED: Use utils.interpolation.interpolate_string instead"""
        return interpolate_string(template, context)
    
    def _interpolate_config(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """DEPRECATED: Use utils.interpolation.interpolate_dict instead"""
        return interpolate_dict(config, context)
```

#### Step 3.2: Run Tests

```bash
# Engine tests should still PASS (compatibility layer)
pytest tests/core/test_engine_interpolation.py -v
pytest tests/ -v
```

#### Step 3.3: Remove Old Implementation (Optional)

Once confirmed working, remove the old methods and update callsites:

```python
# Replace all usages:
# self._substitute_variables(...) → interpolate_string(...)
# self._interpolate_config(...) → interpolate_dict(...)
```

---

### Phase 4: Migrate Actions (1 hour)

#### Step 4.1: Update CompleteJobAction

**File**: `src/statemachine_engine/actions/builtin/complete_job_action.py`

```python
# ADD import
from ...utils.interpolation import interpolate_string

class CompleteJobAction(BaseAction):
    async def execute(self, context: Dict[str, Any]) -> str:
        # REPLACE:
        # job_id = self._interpolate_variables(self.job_id_template, context)
        
        # WITH:
        job_id = interpolate_string(self.job_id_template, context)
        
        # ... rest of code ...
    
    # REMOVE method:
    # def _interpolate_variables(self, template: str, context: Dict[str, Any]) -> str:
    #     ... DELETE THIS METHOD ...
```

**Run Tests**:
```bash
pytest tests/actions/test_complete_job_action.py -v
```

---

#### Step 4.2: Update StartFSMAction

**File**: `src/statemachine_engine/actions/builtin/start_fsm_action.py`

```python
# ADD import
from ...utils.interpolation import interpolate_string

class StartFSMAction(BaseAction):
    async def execute(self, context: Dict[str, Any]) -> str:
        # REPLACE:
        # yaml_path = self._interpolate_variables(self.yaml_path, context)
        # machine_name = self._interpolate_variables(self.machine_name, context)
        
        # WITH:
        yaml_path = interpolate_string(self.yaml_path, context)
        machine_name = interpolate_string(self.machine_name, context)
        
        # ... rest of code ...
    
    # REMOVE methods:
    # def _interpolate_variables(self, template: str, context: Dict[str, Any]) -> str:
    #     ... DELETE THIS METHOD ...
    #
    # def _get_nested_value(self, context: Dict[str, Any], key_path: str) -> Any:
    #     ... DELETE THIS METHOD (no longer needed) ...
```

**Run Tests**:
```bash
pytest tests/actions/test_start_fsm_action.py -v
```

---

#### Step 4.3: Update SendEventAction

**File**: `src/statemachine_engine/actions/builtin/send_event_action.py`

```python
# ADD import
from ...utils.interpolation import interpolate_string

class SendEventAction(BaseAction):
    async def execute(self, context: Dict[str, Any]) -> str:
        # FIND inline replacement (line ~196-200):
        # if isinstance(extracted_value, str) and '{id}' in extracted_value:
        #     substitute_id = event_job_id or job_id
        #     extracted_value = extracted_value.replace('{id}', substitute_id if substitute_id else '{id}')
        
        # REPLACE WITH:
        if isinstance(extracted_value, str):
            extracted_value = interpolate_string(extracted_value, context)
        
        # (More robust - handles all variables, not just {id})
```

**Run Tests**:
```bash
pytest tests/actions/test_send_event_action.py -v
```

---

### Phase 5: Final Validation (30 min)

#### Step 5.1: Run Full Test Suite

```bash
# All tests should PASS
pytest tests/ -v --tb=short

# Check coverage - utils should be 100%
pytest tests/ --cov=statemachine_engine --cov-report=term-missing

# Expected: statemachine_engine/utils/interpolation.py: 100% coverage
```

#### Step 5.2: Check for Remaining Usage

```bash
# Search for any missed duplicates
grep -r "def.*interpolat" src/statemachine_engine/
grep -r "def.*substitut" src/statemachine_engine/

# Should only find:
# - utils/interpolation.py (the shared module)
# - bash_action.py (keeps its unique bash-specific logic)
```

#### Step 5.3: Update Documentation

**File**: `src/statemachine_engine/utils/__init__.py`

```python
"""
Utility modules for statemachine-engine.

This package contains shared utility functions used across the framework.
"""

from .interpolation import interpolate_string, interpolate_dict

__all__ = ['interpolate_string', 'interpolate_dict']
```

**File**: `README.md` - Add section:

```markdown
## Variable Interpolation

The framework supports variable interpolation in configuration strings using `{variable}` syntax.

### Supported Patterns

- **Simple variables**: `{job_id}`, `{status}`, `{machine_name}`
- **Nested access**: `{event_data.payload.job_id}`, `{current_job.id}`
- **Unknown variables**: Preserved as-is (e.g., `{missing}` stays `{missing}`)

### Example

```yaml
states:
  - processing:
      actions:
        - type: log
          message: "Processing job {job_id} with status {status}"
        - type: complete_job
          job_id: "{current_job.id}"
```

Context: `{"job_id": "123", "status": "running", "current_job": {"id": "456"}}`

Output: "Processing job 123 with status running"
```

---

## Migration Checklist

### Pre-Migration
- [ ] Review all 4 duplicate implementations
- [ ] Identify all callsites (done above)
- [ ] Choose master implementation (engine - done)

### Phase 1: Tests
- [ ] Create `tests/utils/test_interpolation.py`
- [ ] Copy/adapt 25+ tests from engine tests
- [ ] Run tests (should FAIL - module doesn't exist yet)

### Phase 2: Implementation
- [ ] Create `src/statemachine_engine/utils/` directory
- [ ] Create `interpolation.py` with functions
- [ ] Run tests (should PASS)

### Phase 3: Engine Migration
- [ ] Import utility in `engine.py`
- [ ] Add compatibility wrapper methods
- [ ] Run engine tests (should PASS)
- [ ] Replace callsites with direct utility calls
- [ ] Remove old methods

### Phase 4: Actions Migration
- [ ] Update `CompleteJobAction`
  - [ ] Import utility
  - [ ] Replace method calls
  - [ ] Remove duplicate method
  - [ ] Run tests
- [ ] Update `StartFSMAction`
  - [ ] Import utility
  - [ ] Replace method calls
  - [ ] Remove duplicate methods
  - [ ] Run tests
- [ ] Update `SendEventAction`
  - [ ] Import utility
  - [ ] Replace inline logic
  - [ ] Run tests

### Phase 5: Validation
- [ ] Run full test suite (`pytest tests/ -v`)
- [ ] Check coverage (utils should be 100%)
- [ ] Search for remaining duplicates
- [ ] Update documentation
- [ ] Update `README.md` with interpolation guide

### Post-Migration
- [ ] Commit changes with descriptive message
- [ ] Update `CHANGELOG.md`
- [ ] Update refactoring analysis document

---

## Benefits

### Code Quality
- ✅ **Single source of truth** - one implementation, one place to fix bugs
- ✅ **Consistent behavior** - all actions use identical logic
- ✅ **Better tested** - 100% coverage for utility module
- ✅ **Reusable** - easy to use in new actions/features

### Maintenance
- ✅ **Easier debugging** - one place to add logging/diagnostics
- ✅ **Simpler upgrades** - enhance once, all users benefit
- ✅ **Clear responsibility** - utils module owns interpolation

### Performance
- ⚠️ **No performance impact** - same regex logic, just better organized

---

## Risks & Mitigation

### Risk 1: Breaking Existing Behavior

**Probability**: LOW  
**Impact**: MEDIUM

**Mitigation**:
- Keep existing tests (15 engine + 3 complete_job + 15 start_fsm = 33 tests)
- Run full test suite after each phase
- Use compatibility wrappers during migration
- Can rollback easily (pure refactor, no logic changes)

### Risk 2: Missing Edge Cases

**Probability**: LOW  
**Impact**: LOW

**Mitigation**:
- Engine implementation is most mature (already handles all cases)
- 25+ comprehensive tests cover edge cases
- No new features added (just extraction)

### Risk 3: Import Circular Dependencies

**Probability**: VERY LOW  
**Impact**: MEDIUM

**Mitigation**:
- `utils/` is a leaf module (no imports from core/actions)
- Simple utility functions (no class dependencies)
- Can verify with import check: `python -c "from statemachine_engine.utils import interpolation"`

---

## Success Criteria

✅ **All tests pass** (235+ existing tests)  
✅ **No duplicate interpolation methods** (except BashAction's unique logic)  
✅ **100% coverage** for utils/interpolation.py  
✅ **Documentation updated** (README, docstrings)  
✅ **Reduced LOC** (~80 lines removed)

---

## Timeline

| Phase | Duration | Parallel? |
|-------|----------|-----------|
| 1. Write Tests | 1 hour | No |
| 2. Implement Module | 1 hour | No |
| 3. Migrate Engine | 30 min | No |
| 4. Migrate Actions | 1 hour | Yes (independent) |
| 5. Final Validation | 30 min | No |

**Total**: 3-4 hours of focused work

---

## Next Actions

1. **Review this plan** with team (if applicable)
2. **Create feature branch**: `git checkout -b refactor/interpolation-utility`
3. **Start Phase 1**: Create test file with 25+ tests
4. **Commit after each phase**: Small, testable increments

---

## References

- Engine implementation: `src/statemachine_engine/core/engine.py:637-703`
- Engine tests: `tests/core/test_engine_interpolation.py` (15 tests)
- CompleteJobAction: `src/statemachine_engine/actions/builtin/complete_job_action.py:68-78`
- StartFSMAction: `src/statemachine_engine/actions/builtin/start_fsm_action.py:224-267`
- Coverage report: `docs/refactoring-analysis-2025-11.md`
