# Feature Request: Pipeline Logging and Monitoring

**Priority:** HIGH
**Type:** Enhancement
**Status:** Proposed
**Effort:** 1 day
**Requested:** 2026-04-29

## Summary

The pipeline FSM subprocess produces no accessible logs. When the pipeline gets
stuck or fails, the only diagnostic tool is querying SQLite for the current
state. Add per-pipeline log files and a unified log viewer.

## Value Statement

Operators can diagnose stuck or failed pipelines without guessing — every state
transition, action output, and error is in a dedicated log file.

## Problem

### Current state

| Component | Logging | Accessible? |
|-----------|---------|-------------|
| Dispatcher | `logs/fsm-dispatcher.log` (stdout+stderr redirect) | ✅ Yes |
| UI server | `logs/fsm-ui.log` (stdout+stderr redirect) | ✅ Yes |
| Pipeline subprocess | Python `logging.basicConfig` → stderr | ❌ Lost |
| Pipeline bash actions | `asyncio.create_subprocess_shell(stdout=PIPE, stderr=PIPE)` | ❌ Captured but truncated to 200 chars in parent logger |
| Old watcher2.sh | `exec > >(tee -a "$LOG_FILE") 2>&1` — everything in one file | ✅ Was accessible |

The pipeline is launched by the dispatcher's `bash` action type. The `bash_action.py`
captures stdout/stderr via `asyncio.subprocess.PIPE`, but:

1. **stdout** is only logged at `DEBUG` level, truncated to 200 chars
2. **stderr** is logged at `WARNING` level, truncated to 200 chars
3. The pipeline itself uses `logging.basicConfig(level=INFO, ...)` which goes to
   stderr of the subprocess — captured by the parent's PIPE but mostly discarded
4. The pipeline spawns its **own** bash actions (preflight, worktree_setup, etc.)
   which each capture stdout/stderr via PIPE — nested capture, no file output
5. No `--log-file` option exists on the `statemachine` CLI

### Consequences

- Cannot diagnose why pipeline is stuck in a state (e.g. `worktree_setup`)
- Cannot see action output (git commands, preflight checks, etc.)
- The validate-fsm-single.sh script works around this with `2>&1 | tee "$LOG_FILE"`
  but the production start-system.sh does not

### What old watcher2.sh did right

```bash
LOG_FILE="logs/watcher2-run-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1
```

All output — including subprocess output — went to both terminal and log file.

## Proposed Solution

### Phase 1: Immediate — Log redirect in dispatcher config (this project)

Add `2>&1 | tee` to the pipeline launch command in `watcher-dispatcher.yaml`:

```yaml
processing_topic:
    - type: bash
      command: |
        TOPIC="{topic_file}"
        BASENAME=$(basename "$TOPIC" .md)
        LOG="logs/fsm-pipeline-${BASENAME}-$(date +%H%M%S).log"
        statemachine .chaplain/config/watcher-pipeline.yaml \
          --actions-dir .chaplain/actions \
          --initial-context "{\"topic_file\":\"$TOPIC\"}" \
          --debug \
          2>&1 | tee "$LOG"
      success: topic_done
      error: error
      timeout: 1800
```

**Pros**: Zero engine changes, works now.
**Cons**: Only captures top-level pipeline logging, not nested action output.

### Phase 2: Engine — `--log-file` flag (statemachine-engine FR)

Add `--log-file PATH` to the `statemachine` CLI:

```python
# cli.py
parser.add_argument("--log-file", help="Write logs to file (in addition to stderr)")

# In run_state_machine():
if log_file:
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(...))
    logging.getLogger().addHandler(file_handler)
```

Usage:
```bash
statemachine config.yaml --log-file logs/pipeline-$TOPIC.log --debug
```

### Phase 3: Engine — Action output forwarding (statemachine-engine FR)

`bash_action.py` currently captures subprocess output in PIPE and only logs
truncated snippets. Instead, stream output to both the logger and a file:

```python
# Instead of: stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
# Use: stream to log file + capture for event routing
```

### Phase 4: UI — Log viewer panel

Add a log viewer tab to the UI that:
- Lists available log files from `logs/fsm-pipeline-*.log`
- Streams content in real-time via WebSocket
- Highlights errors and state transitions

## Acceptance Criteria

### Phase 1 (this project — watcher-dispatcher.yaml)
- [ ] Pipeline subprocess output written to `logs/fsm-pipeline-<topic>-<timestamp>.log`
- [ ] Log file path visible in dispatcher startup output
- [ ] Old log rotation: keep last 20 pipeline logs

### Phase 2 (statemachine-engine FR)
- [ ] `statemachine --log-file PATH` writes all logging output to file
- [ ] File logging is in addition to stderr (not replacing)
- [ ] Works with `--debug` flag

### Phase 3 (statemachine-engine FR)
- [ ] `bash_action.py` streams full subprocess output (not truncated)
- [ ] Output appears in engine log file at DEBUG level
- [ ] Stderr from subprocesses logged at WARNING level

### Phase 4 (statemachine-engine FR)
- [ ] UI shows log viewer tab for active/recent pipelines
- [ ] Real-time streaming of new log lines

## Alternatives Considered

**Single monolithic log (watcher2.sh pattern):** The old `exec > >(tee ...)`
captured everything in one file. Simple, but mixes dispatcher and pipeline
output when running multiple topics. Per-pipeline log files are better for
debugging.

**Structured JSON logging:** Overkill for current scale. Plain text with
timestamps is sufficient. Can add later if needed.

## Related

- `start-system.sh:249`: Dispatcher redirect `> logs/fsm-dispatcher.log 2>&1`
- `validate-fsm-single.sh:72`: Uses `2>&1 | tee "$LOG_FILE"` (the pattern to copy)
- `watcher2.sh:22`: `exec > >(tee -a "$LOG_FILE") 2>&1` (old global capture)
- `cli.py:29`: `logging.basicConfig()` — no file handler
- `bash_action.py:232`: `stdout=asyncio.subprocess.PIPE` — captures but discards
- `bash_action.py:263`: Truncates output to 200 chars in logger
