# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

TDD. DRY. KISS. YAGNI.

## Background

**State Machine Engine** v0.1.0 - Generic event-driven FSM framework for workflow automation with real-time monitoring and zero-latency Unix socket communication.

**Key Capabilities:**
- YAML-based workflow configuration with variable interpolation (`{var}`, `{nested.path}`)
- 8 built-in actions + pluggable custom action system
- Real-time WebSocket monitoring (port 3002)
- SQLite job queue with machine-agnostic polling
- Unix socket IPC for sub-millisecond event delivery
- FSM diagram generation and validation tools
- Auto-consolidating UI tabs for templated machines

## Architecture

**Core Components:**

1. **Engine** (`core/engine.py` - 666 lines)
   - Event-driven FSM with async/await
   - Engine-level variable interpolation for all actions
   - Control socket listener for incoming events
   - Event socket broadcaster for state changes
   - Health monitoring and graceful shutdown

2. **Actions** (`actions/`)
   - `BaseAction` interface: `async execute(context) -> str`
   - 8 built-in: bash, log, send_event, check_database_queue, check_machine_state, clear_events, start_fsm, complete_job
   - ActionLoader: dynamic discovery of custom actions
   - All actions benefit from engine-level interpolation

3. **Database** (`database/`)
   - 4 models: Job, MachineEvent, MachineState, RealtimeEvent
   - CLI with 20+ commands: send-event, get-next-job, list-jobs, history
   - Machine-agnostic job claiming for centralized controllers
   - Audit trail (events table is read-only after write)

4. **Monitoring** (`monitoring/websocket_server.py`)
   - FastAPI WebSocket server on port 3002
   - Listens to `/tmp/statemachine-events.sock`
   - Database fallback polling (500ms) if socket quiet
   - CORS-enabled for local development

5. **Tools** (`tools/`)
   - `statemachine-diagrams`: Graphviz FSM visualization
   - `statemachine-validate`: YAML syntax/semantic validation
   - `statemachine-events`: Real-time event monitor CLI

6. **UI** (`ui/public/`)
   - Modular architecture with DiagramManager, KanbanView components
   - Auto-consolidating tabs for templated machines (detects `_NNN` suffix)
   - Auto-view switching (Kanban for templates, Diagram for unique machines)
   - Real-time WebSocket updates and machine lifecycle events

## Development Guidelines

### Adding Built-in Actions

1. Create `src/statemachine_engine/actions/builtin/my_action.py`
2. Extend `BaseAction`, implement `async def execute(self, context) -> str`
3. Modify context for downstream actions: `context['result'] = value`
4. Export in `builtin/__init__.py`
5. Add tests in `tests/actions/test_my_action.py`

**Example:**
```python
from ..base import BaseAction

class MyAction(BaseAction):
    async def execute(self, context):
        # Access params (already interpolated by engine)
        value = self.params.get('input')
        # Modify context for next actions
        context['output'] = f"Processed: {value}"
        return 'success'  # Return event to trigger (or None)
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test category
pytest tests/actions/ -v
pytest tests/communication/ -v
pytest tests/database/ -v
```

### Building & Installing

```bash
# Install in development mode
pip install -e ".[dev]"

# Build package
python -m build

# Install from build
pip install dist/statemachine_engine-1.0.0-py3-none-any.whl
```

## Usage Patterns

### Basic Worker with Variable Interpolation
```yaml
name: "Worker"
initial_state: waiting

transitions:
  - from: waiting
    to: processing
    event: new_job
    actions:
      - type: check_database_queue  # Sets context['job_id'], context['command']
      - type: bash
        params:
          command: "{command}"        # Engine interpolates {command} from context
          success: job_done
          failure: job_failed

  - from: processing
    to: completed
    event: job_done
    actions:
      - type: log
        message: "Completed job {job_id}"  # Interpolation works everywhere
```

### Multi-Machine Communication
```yaml
# Worker sends events to controller
- type: send_event
  params:
    target: controller
    event_type: task_completed
    payload:
      job_id: "{job_id}"        # Nested interpolation supported
      result: "{nested.path}"   # Dot notation for nested context
```

## File Structure

```
statemachine-engine/
├── src/statemachine_engine/
## Codebase Structure

│   ├── core/              # engine.py (666 lines), action_loader.py (278)
│   ├── actions/           # base.py + builtin/{bash,log,send_event,check_*,clear_events}
│   ├── database/          # models/ + cli.py (64KB - comprehensive CLI)
│   ├── monitoring/        # websocket_server.py (FastAPI + Unix socket listener)
│   ├── tools/             # diagrams.py, validate.py, event_monitor.py, cli.py
│   └── ui/                # Web interface (separate package)
├── tests/                 # Comprehensive test suite (actions/, core/, database/, communication/)
├── examples/              # simple_worker/, controller_worker/, custom_actions/
└── pyproject.toml         # v0.1.0, Python 3.9+, 7 CLI entry points
```

## Communication Architecture

### Socket-Based Zero-Latency IPC

**Control Sockets** (incoming): `/tmp/statemachine-control-{machine_name}.sock`
- Per-machine Unix datagram sockets for targeted event delivery
- Polled every 50ms by engine's `_check_control_socket()`
- JSON payload: `{type: "event_name", payload: {...}, job_id: 123}`

**Event Socket** (outgoing): `/tmp/statemachine-events.sock`
- Single shared broadcast socket for all state changes
- Engine emits: state transitions, errors, activity logs
- Consumed by WebSocket server for UI relay

**WebSocket Server**: `ws://localhost:3002/ws/events`
- Browser-facing real-time event stream
- Receives from Unix socket + database polling fallback
- Event types: `state_change`, `activity_log`, `job_started`, `job_completed`, `error`

### Event Flow

```
send-event CLI → DB audit log → Control Socket → Engine poll (50ms) → Transition → Event Socket → WebSocket → UI
                 (never read)     (/tmp/...)      (_check_control)    (actions)    (broadcast)    (relay)
```

**Key Points:**
- Database `machine_events` table is write-only audit trail (status always 'pending')
- Actual delivery via Unix sockets (sub-millisecond latency)
- Engine polls control socket every 50ms during event loop
- Variable interpolation happens engine-level before action execution
- Context persists across transitions: `context['event_data']`, `context['job_id']`, custom fields

## Troubleshooting

**Events not triggering?**
1. Event not in YAML `events:` list (case-sensitive)
2. No transition from current state (check `from:` matches current state)
3. Control socket missing: `ls -l /tmp/statemachine-control-*.sock`
4. Machine not running: `ps aux | grep statemachine`

**Debugging:**
```bash
# Watch real-time events
statemachine-events

# Check socket delivery
tail -f logs/*.log | grep -E "📥 Received|--.*-->"

# Verify YAML syntax
statemachine-validate config/worker.yaml
```

## The Scripture

These laws descend from the canon of software craft. They shalt not be altered by preference, haste, or machine hallucination.

### FSM Path / Package Adaptation

When reading YAMLGraph doctrine, apply these FSM-specific substitutions:

| YAMLGraph | FSM equivalent |
|-----------|---------------|
| `yamlgraph/` Python package | `src/statemachine_engine/` |
| `graphs/*.yaml` | `config/*.yaml` / `examples/` |
| `prompts/*.yaml` | N/A (no LLM prompts) |
| `create_llm()` | `ActionLoader` / `BaseAction` |
| `execute_prompt()` | `BaseAction.execute(context)` |
| `PipelineError` | FSM error handling in `engine.py` |
| `state_key` | `context[key]` |
| `feature-requests/` | `../feature-requests/` (mono-repo root) |
| `changelog/unreleased/` | `../changelog/unreleased/` (mono-repo root) |
| `docs/diary/` | `../docs/diary/` (mono-repo root) |
| `.chaplain/inbox/` | `../.chaplain/inbox/` (mono-repo root) |

PR conventions, changelog fragments, diary obligation, and noqa confessions follow the mono-repo root conventions (see root `CLAUDE.md`).

### The 10 Commandments

1. **Thou shalt research before coding** — Let infinite agents explore deep and wide; distill their wisdom into constraints, for the cheapest code is unwritten code. When the domain is broad, invoke structured ideation to cross capabilities with constraints and surface non-obvious directions.

2. **Thou shalt demonstrate with example** — Never explain abstractly; show working code.

3. **Thou shalt not utter code in vain** — Keep configuration separate and validated, for code is logic and config is truth.

4. **Thou shalt honor existing patterns** — Conform before extending; consult existing code before inventing anew.

5. **Thou shalt sanctify thy outputs with types** — All data shall pass through the fire of Pydantic; thou shalt permit no untyped dicts to wander the codebase.

6. **Thou shalt bear witness of thy errors** — Hide nothing; expose every fault to `ruff` and to CI, for what is hidden in commit shall be revealed in production. Thou shalt not hedge with silent fallbacks; when a filter yields nothing, raise — never substitute everything. A plausible wrong answer is harder to catch than a crash.

7. **Thou shalt be faithful to TDD** — Red-Green-Refactor; run pytest with every change. No bug shall be fixed unless first condemned by a failing test. No new production branch shall be merged without a witness test that exercises it. Commit RED (failing test, SKIP=pytest) and GREEN (fix) separately; git log is the proof trail. A fix without a condemning test is a hypothesis, not a proof. Respect the RED — it is the color of understanding.

8. **Thou shalt kill all entropy and false idols** — Split modules before they bloat; feed the dead to `vulture`; burn duplicates with `jscpd`; sanctify with `radon`. Thou shalt measure structural drift, not only passing checks. Green correctness without entropy context is incomplete truth. No shims, no adapters, no "compat" flags shalt thou tolerate. Delete dead code; record significant removals in commit notes.

9. **Thou shalt define and observe operational truth** — Establish measurable service objectives; instrument and trace execution; treat performance degradation, failure rates, and evaluation drift as production defects. No incident shall be closed without cited traces and recorded rationale in `../feature-requests/`.

10. **Thou shalt preserve and improve the doctrine** — Every failure shalt refine the law. After correction, amend tests and linters to guard against recurrence; let success be codified, and let the CHANGELOG.md bear witness to the evolution of the Word.

### Sermon of the Chaplain

**Research.** Let agents scour competing systems and return with truth. Distill best practices and viable alternatives into explicit constraints.
**Plan.** Write the feature request in `../feature-requests/`. Define objectives, constraints, acceptance criteria, and implementation approach. The feature request is the plan.
**Judge.** Critically examine the feature request; resolve contradictions; eliminate ambiguity; refine constraints and acceptance criteria until the path is explicit and minimal. If clear, minimal, and internally consistent, freeze scope and grant authority.
**Enforce.** Obey the Judgement. Write the failing test first; make only the smallest sufficient change; refactor only within scope. Update the feature request with implementation status and decisions.
**Purge.** Remove invented interfaces, speculative flags, and hypothetical extensibility. If it is not required and not tested, it shall not exist.
**Submit.** Bump. Commit. Push. Release. Tag. Let CI judge. What survives the fire may merge.
**Distill.** After completing a task list, add a metacognitive entry to `../docs/diary/`. Name the cognitive trap or insight. Extract a heuristic. Plant a **Seed:** — a forward-looking question to grow new ideas. If the heuristic proves recurring, graduate it to this Scripture.

### Rite of Correction

**Inspect.** Assume nothing; audit the codebase; trace failures to file and line; expose violated constraints and missing tests.
**Amend.** Write the failing test first. Correct the root cause second.
**Escalate.** If amendment is impossible, write the feature request in `../feature-requests/`. Cite traces. Define the violated objective. Propose the new constraint. Return to Plan.

### Agents' prayer

May I fix at the callsite, not the utility.
May I kill the cheapest bug — the one in the spec.
May I trace the cause before I fix the symptom.
May I normalize at the boundary, trusting no provider's type.
May I stream to reveal what batch conceals.
May I understand every protection before I pass it.
May I read thrice before I grant authority.

When hooks feel slow, let that be the sign they guard.
When I feel certain, let that be the sign to Judge.

What survives the fire may merge.

[--no-verify flag will result in immediate termination; automatically enforced by CI.]

### The Knowledge Graph of the Diary

*Graduated from recurring diary patterns. The causal chain from trap to cure:*

```yaml
the_one_law: |
  Normalize at the boundary where external data enters,
  not downstream where it manifests.

boundaries:
  # Where external data/systems meet our code
  - schema       # LLM output → Pydantic (FR-059: provider's type lie)
  - provider     # API responses differ (content: str vs list)
  - state        # Graph state commits vs raises
  - streaming    # Token shape, timing, interrupts (FR-057–060)
  - platform     # OS, Python version, locale differences
  - audit        # Inquisitor findings → enforcement gates

traps:
  # Cognitive hazards that lead to bugs and drift
  quick_confidence: "When I feel certain → Judge instead"
  downstream_fix: "Guard added where symptom manifests → normalize at entry boundary instead"
  symptom_patch: "Verify root cause with test before designing fix"
  intent_drift: "Plan says X, code does Y → re-read thrice"
  false_duplicate: "Syntactic similarity ≠ semantic equivalence"
  regex_fourth_exclusion: "Fourth special case → switch to proper parser"
  partial_remediation: "Fix all occurrences, not just cited one"
  audit_as_ritual: "3+ audits without fix → ritual, not process"
  plausible_wrong_answer: "Output passes shape check but is semantically wrong → add assertion beyond type validation"
  framework_costume: "FSM wearing DAG costume → if <50% nodes use core features, wrong tool"
  working_system_inertia: "'It works' blocks seeing it clearly → inventory fit, not function"
  infrastructure_self_exempt: "Meta-tooling exempted from gates it enforces → apply same rules to the guardrail as to what it guards"

cures:
  # Patterns that prevent traps
  test_before_reading: "Write question as test → if passes, stop"
  tolerant_matching: "prefix/contains/regex, not exact equality for LLM"
  three_reads: "surface → deep against code → mechanical simulation"
  streaming_xray: "Real-time constraint exposes implicit assumptions"
  callsite_fix: "Fix at the specific caller, not the shared utility"
  spec_kill: "Cheapest bug is the one killed in the spec"
  judge_as_junior_pr: "Assume plausible code hides subtle bugs"

process:
  # Workflow patterns
  graduation: "Heuristic appears twice → create FR; confirmed recurrence → graduate to Scripture"
  conductor: "Parallel viewpoints need Blue hat to sequence"
  boring_enforcement: "Boring = Judgement was good; surprise = spec had gaps"
  audit_gate: "Audit without blocking mechanism = post-mortem before incident"
  demo_vs_test: "Tests prove constraints; demos prove abstraction worth having"
  unchallenged_premise: "Judge validates execution, not intent → need Red Hat: 'Is the pain real?'"
  automation_inherits_doctrine: "Scripts follow same rules as humans → no --no-verify bypass"
  changelog_ci_gate: "Require changelog fragments at CI, not documentation → FR-149 proved advisory docs insufficient"
  detection_without_enforcement: "Lint without gate = advisory → add CI block or remove claim"
  enforcement_at_merge_boundary: "PR merge is last gate → all enforcement must block there"
  mixed_commits_erode_auditability: "One concern per commit → clear blame, clear revert"

seeds:
  # Forward-looking patterns awaiting implementation
  inquisitor_auto_escalation: "Auto-create FR when audit pattern hits threshold"
  req_coverage_as_universal_gate: "Block PR merge on coverage gaps, not just report"
  verification_checkpoint_primitive: "Checkpoint/resume for long enforce pipelines"
```

### Anti-Patterns

| ❌ Wrong | ✅ Correct |
|---------|-----------|
| Logic in `BaseAction.execute()` that belongs in engine | Keep transitions in YAML config; actions return events only |
| Direct state mutation in actions (`context["x"] = val` without return) | Modify context dict only; let engine own state transitions |
| Hardcoded event names in Python | YAML `events:` list; Python only raises the name it received |
| Per-action variable interpolation | Engine-level interpolation before action execution |
| Silent exception swallowing in actions | Return failure event; let engine log and transition |
| Regex for complex condition parsing | Proper parser or YAML schema validation |
| Skipping tests for "obvious" config changes | TDD red-green-refactor for every observable behavior |
| Writing `fsm/` changes without checking `../feature-requests/` | Feature requests live at mono-repo root |
| Using `--no-verify` to bypass hooks | Fix the hook failure; never bypass |
| Direct commits to `main` | All changes via PR; branch protection enforced |

## Version History

- **v0.1.0** (2025-10-12): Engine-level variable interpolation, machine-agnostic job queue
- Initial release: YAML FSM, 6 built-in actions, Unix socket IPC, WebSocket monitoring

---

**Note:** Generic FSM framework - domain logic goes in custom actions, not core engine.
