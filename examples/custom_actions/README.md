# Custom Actions Example

This example demonstrates using custom actions with the `--actions-dir` parameter.

## Structure

```
custom_actions/
├── README.md                 # This file
├── actions/                  # Custom actions directory
│   ├── greet_action.py      # Simple custom action
│   └── calculate_action.py  # Another custom action
└── config/
    └── worker.yaml          # State machine configuration
```

## Custom Actions

### greet_action.py

A simple custom action that greets a user.

### calculate_action.py

A custom action that performs a calculation.

## Running the Example

```bash
cd examples/custom_actions

# Run with custom actions directory
statemachine config/worker.yaml \
  --machine-name custom_worker \
  --actions-dir ./actions
```

## Key Features Demonstrated

1. **No Package Installation**: Custom actions work without `pip install -e .`
2. **Simple Structure**: Actions live alongside configs
3. **Fast Iteration**: Edit → Test immediately
4. **Clear Organization**: Project-specific actions in project directory

## Sending Events

```bash
# Trigger greeting
statemachine-db send-event \
  --target custom_worker \
  --type greet \
  --payload '{"name": "Alice"}'

# Trigger calculation
statemachine-db send-event \
  --target custom_worker \
  --type calculate \
  --payload '{"a": 5, "b": 3}'
```

## Benefits

- ✅ No setup.py or pyproject.toml needed
- ✅ Actions discoverable automatically
- ✅ Supports nested action directories
- ✅ Works with relative and absolute paths
