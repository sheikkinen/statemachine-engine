# Quickstart Guide

Get started with State Machine Engine in 5 minutes.

## Installation

```bash
pip install statemachine-engine
```

## Your First State Machine

### 1. Create a Configuration

Create `hello.yaml`:

```yaml
name: "Hello World"
initial_state: greeting

states:
  - greeting
  - done

events:
  - greet
  - finished

transitions:
  - from: greeting
    to: done
    event: greet
    actions:
      - type: bash
        params:
          command: "echo Hello from State Machine!"
          success: finished
```

### 2. Run It

```bash
statemachine hello.yaml --machine-name hello
```

You'll see:
```
Hello from State Machine!
```

## Adding Job Processing

Create `worker.yaml`:

```yaml
name: "Job Worker"
initial_state: waiting

transitions:
  - from: waiting
    to: processing
    event: new_job
    actions:
      - type: check_database_queue
        params:
          job_type: my_task

  - from: processing
    to: waiting
    event: job_done
    actions:
      - type: bash
        params:
          command: "echo Processing job {job_id}"
          success: job_done
```

## Custom Actions

Create `my_action.py`:

```python
from statemachine_engine.actions import BaseAction

class MyAction(BaseAction):
    async def execute(self, context):
        job_id = context.get('job_id')
        print(f"Processing {job_id}")
        return 'success'
```

Use in YAML:

```yaml
actions:
  - type: my_action
    params:
      success: job_done
```

## Multi-Machine Setup

Start multiple machines that communicate:

```bash
# Terminal 1
statemachine controller.yaml --machine-name controller

# Terminal 2  
statemachine worker.yaml --machine-name worker
```

Workers can send events to controller:

```yaml
actions:
  - type: send_event
    params:
      target: controller
      event_type: task_completed
      payload:
        job_id: "{job_id}"
```

## What's Next?

- See [examples/](../examples/) for complete working examples
- Read [architecture.md](architecture.md) for system design
- Check [api.md](api.md) for detailed API reference
