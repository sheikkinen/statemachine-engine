# Timeout Event Demo

This example demonstrates the **timeout event feature** - automatic state transitions that fire after a specified duration if no other events occur.

## Timeout Syntax

Add timeout transitions using the special `timeout(N)` event syntax:

```yaml
transitions:
  - from: waiting
    to: timed_out
    event: timeout(5)   # Fires after 5 seconds if still in 'waiting' state
```

## How It Works

1. **State Entry**: When entering a state with timeout transitions, the engine starts an asyncio timer task
2. **Timer Active**: The timer counts down in the background
3. **Event Cancels**: If ANY other event arrives, the timer is cancelled
4. **Timeout Fires**: If the timer completes, the timeout event is automatically processed

## Running the Demo

```bash
# From the examples/timeout_demo directory
cd examples/timeout_demo

# Run the timeout worker
statemachine-cli run config/timeout_worker.yaml
```

## What Happens

1. **Initialization**: Worker starts and initializes
2. **Waiting State**: 
   - Enters `waiting` state with 5-second timeout
   - Logs: "⏳ Waiting for work (5-second timeout active)..."
   - If you don't send an event within 5s → transitions to `timed_out`
3. **Timeout Triggered**:
   - Logs: "⏰ TIMEOUT! Operation took too long"
   - Waits 3 seconds, then retries (goes back to `waiting`)
4. **Manual Event** (optional):
   - Send `start_work` event to cancel timeout and move to `processing`
   - Processing state has its own 10-second timeout

## Sending Events

To cancel the timeout and send manual events:

```bash
# Send start_work event (cancels the 5s timeout in waiting state)
echo '{"type": "start_work", "payload": {}}' | nc -U /tmp/statemachine-control-timeout_worker.sock

# Send work_done event (completes processing before 10s timeout)
echo '{"type": "work_done", "payload": {}}' | nc -U /tmp/statemachine-control-timeout_worker.sock
```

## Use Cases

Timeout events are useful for:

- **Watchdog timers**: Ensure states don't hang indefinitely
- **Retry logic**: Retry failed operations after a delay
- **Polling intervals**: Periodically check for conditions
- **Graceful degradation**: Fall back to alternate paths when operations are slow
- **Resource cleanup**: Clean up stale resources after inactivity

## Multiple Timeouts

You can have multiple timeout transitions from the same state:

```yaml
transitions:
  - from: waiting
    to: short_timeout
    event: timeout(5)    # Short timeout path
  
  - from: waiting
    to: long_timeout
    event: timeout(30)   # Long timeout path (won't fire if short fires first)
```

**Note**: Only the shortest timeout will fire, as entering a new state cancels all active timeouts.
