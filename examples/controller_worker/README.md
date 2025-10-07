# Controller/Worker Example

Demonstrates multi-machine coordination with event-driven communication.

## Architecture

- **Controller**: Monitors task completion events from workers
- **Worker**: Processes jobs and notifies controller when done

## Configuration

### Controller (config/controller.yaml)
- Stays in `monitoring` state
- Receives `task_completed` events from worker
- Logs completion information

### Worker (config/worker.yaml)
- Checks database queue for jobs
- Processes jobs
- Sends events to controller on completion

## Run

Start both machines:
```bash
./run.sh
```

Or manually:
```bash
# Terminal 1
statemachine config/controller.yaml --machine-name controller

# Terminal 2
statemachine config/worker.yaml --machine-name worker
```
