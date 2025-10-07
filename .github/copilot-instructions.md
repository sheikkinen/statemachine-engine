# Copilot Instructions for State Machine Engine

This workspace provides a **generic state machine framework**. When using GitHub Copilot or Copilot Chat, follow these guidelines:

## Development Style

- Write clean, well-tested code
- Follow Python best practices (PEP 8, type hints)
- Add docstrings to public APIs
- Keep code generic (no domain-specific logic)
- Use async/await for I/O operations

## Architecture Principles

1. **Generic First**: This is a library, not an application
   - No hard-coded domain logic
   - All domain-specific code goes in custom actions
   - Configuration via YAML, not code

2. **Plugin System**: Actions are discoverable and loadable
   - Follow naming convention: `*_action.py` contains `*Action` class
   - Extend `BaseAction` interface
   - Return event names from `execute()`

3. **Event-Driven**: All state changes via explicit events
   - No implicit transitions
   - Actions emit events
   - Engine processes events

4. **Testable**: Mock-friendly architecture
   - Dependency injection
   - Clear interfaces
   - Isolated tests

## Code Patterns

### Adding Built-in Actions

```python
# src/statemachine_engine/actions/builtin/my_action.py
from ..base import BaseAction

class MyAction(BaseAction):
    """
    Brief description.

    YAML Usage:
        actions:
          - type: my_action
            params:
              param1: value1
    """

    async def execute(self, context):
        param1 = self.config.get('param1')
        # Implementation
        return 'success'
```

### Testing Actions

```python
# tests/actions/test_my_action.py
import pytest
from statemachine_engine.actions.builtin import MyAction

@pytest.mark.asyncio
async def test_my_action():
    action = MyAction({'param1': 'test'})
    context = {}
    result = await action.execute(context)
    assert result == 'success'
```

## Documentation

- Update README.md for user-facing changes
- Update docs/api.md for API changes
- Include examples for new features
- Add YAML examples to action docstrings

## Testing

```bash
# Run tests before committing
pytest tests/ -v

# Check coverage
pytest tests/ --cov=statemachine_engine --cov-report=html
```

## Style Guide

- **Tokens over time**: Estimate effort in tokens, not hours
- **Minimal documentation**: Code should be self-documenting
- **Incremental development**: Small, working changes
- **No boilerplate**: Skip unnecessary comments and docstrings for internal code

## References

- See `CLAUDE.md` for architecture details
- See `docs/` for API reference
- See `examples/` for usage patterns

---

**This is a generic framework** - domain-specific code belongs in custom actions, not in the core engine.
