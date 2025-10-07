# Simple Worker Example

A basic state machine that processes jobs from a database queue.

## Configuration

The worker transitions through three states:
- `waiting` - Checks database queue for new jobs
- `processing` - Processes the job
- `completed` - Job finished

## Run

```bash
statemachine config/worker.yaml --machine-name worker
```

Or using Python:
```bash
python -m statemachine_engine.cli config/worker.yaml --machine-name worker
```
