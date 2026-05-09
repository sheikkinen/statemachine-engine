# Feature Request: Project Manifest & `statemachine-system` CLI

**Priority:** HIGH
**Type:** Feature
**Status:** Proposed
**Effort:** 3 days
**Requested:** 2026-04-28

## Summary

Add a project-level manifest (`statemachine-project.yaml`) and a `statemachine-system` CLI that replaces hand-written startup scripts with declarative configuration. The engine already knows everything needed — configs, machine names, actions dirs — but each project rewrites ~300 lines of bash boilerplate to wire it together.

## Value Statement

Project authors declare their machines in 10 lines of YAML instead of writing 300 lines of startup shell; the engine handles cleanup, validation, diagrams, UI, process management, signals, and health checks.

## Problem

Every statemachine-engine project needs a startup script that:
1. Kills stale processes
2. Validates configs
3. Generates diagrams
4. Starts the UI (creates event socket)
5. Starts machines in dependency order
6. Manages PID files
7. Handles SIGINT/SIGTERM cleanup
8. Runs a keep-alive loop

Three projects (statemachine-engine examples, image-generator-fsm, yamlgraph watcher) have independently written this same script:

| Project | Lines | Project-Specific Lines | Boilerplate % |
|---------|-------|----------------------|---------------|
| yamlgraph watcher | 286 | ~17 | 94% |
| image-generator-fsm | 419 | ~28 | 93% |
| fsm examples | 174 | ~12 | 93% |
| **Total** | **879** | **~57** | **93%** |

The project-specific content is only: which configs to load, what initial context to pass, and which machines are spawned by others vs started directly.

This is the **framework costume** trap from the Knowledge Graph: 93% shared infrastructure wearing a per-project shell costume.

## Proposed Solution

### 1. Project Manifest: `statemachine-project.yaml`

```yaml
# statemachine-project.yaml
project:
  name: watcher2
  ui_port: 3001
  actions_dir: .chaplain/actions
  logs_dir: logs
  data_dir: data

machines:
  dispatcher:
    config: .chaplain/config/watcher-dispatcher.yaml
    initial_context:
      inbox_dir: .chaplain/inbox
    start: true  # started by statemachine-system

  pipeline:
    config: .chaplain/config/watcher-pipeline.yaml
    start: false  # spawned by dispatcher, not started directly
```

Image-generator-fsm equivalent:

```yaml
project:
  name: image-generator
  ui_port: 3001
  logs_dir: logs

machines:
  controller:
    config: controller/config/controller.yaml
    actions_dir: controller/actions
    start: true

  sdxl_generator:
    config: sdxl_generator/config/sdxl_generator.yaml
    actions_dir: sdxl_generator/actions
    start: true

  face_processor:
    config: face_processor/config/face_processor.yaml
    actions_dir: face_processor/actions
    start: true

  backstory_workflow:
    config: backstory_workflow/config/backstory_workflow.yaml
    actions_dir: backstory_workflow/actions
    start: true
```

### 2. CLI: `statemachine-system`

```bash
# Start everything (validates, generates diagrams, starts UI, starts machines)
statemachine-system start

# Start with overrides
statemachine-system start --context dispatcher.inbox_dir=.chaplain/inbox-fsm

# Stop all machines
statemachine-system stop

# Status of all machines
statemachine-system status

# Validate only (no start)
statemachine-system validate
```

### 3. Startup Sequence (built into the engine)

The engine implements the same 5-phase sequence every project needs:

```
Phase 0: Prerequisites
  - Locate statemachine-project.yaml (cwd or --project flag)
  - Verify all config files exist
  - Verify actions dirs exist
  - Create logs/ and data/ dirs

Phase 1: Cleanup
  - Kill processes by PID files (logs/<machine>.pid)
  - pkill fallback for orphans
  - Remove stale event socket
  - Reset or preserve DB (--keep-db flag)

Phase 2: Validate & Diagrams
  - statemachine-validate for each config
  - statemachine-diagrams for each config → docs/fsm-diagrams/

Phase 3: Start UI
  - statemachine-ui --port <ui_port> --project-root .
  - Wait for event socket (poll, max 10s)
  - Wait for HTTP (poll, max 10s)

Phase 4: Start Machines
  - Only machines with start: true
  - Per-machine: statemachine <config> --actions-dir <dir> --initial-context <json>
  - Write PID file per machine
  - Verify PID alive after 2s

Phase 5: Keep-alive + signal handling
  - trap SIGINT/SIGTERM → stop all by PID → pkill fallback
  - Print status summary
  - Block until signal
```

### 4. Extension Points

For projects that need custom steps:

```yaml
project:
  hooks:
    pre_start: scripts/custom-preflight.sh   # run before Phase 4
    post_start: scripts/seed-test-data.sh     # run after Phase 4
    pre_stop: scripts/graceful-drain.sh       # run before cleanup
```

This keeps the 5% project-specific logic in small, focused scripts instead of reimplementing the 95% boilerplate.

## Acceptance Criteria

- [ ] `statemachine-project.yaml` schema defined and validated by Pydantic
- [ ] `statemachine-system start` implements the 5-phase sequence
- [ ] `statemachine-system stop` kills all machines by PID + fallback
- [ ] `statemachine-system status` shows machine states from DB
- [ ] `statemachine-system validate` runs validation + diagram generation
- [ ] `--context key.path=value` overrides initial_context at start
- [ ] `--keep-db` flag preserves database across restarts
- [ ] Hooks (`pre_start`, `post_start`, `pre_stop`) execute if defined
- [ ] Machines with `start: false` are not started (spawned by parent)
- [ ] PID files written per machine for deterministic cleanup
- [ ] Signal handling: SIGINT/SIGTERM triggers orderly shutdown
- [ ] Replaces yamlgraph `start-system.sh` as validation (FR-296 becomes thin wrapper or deleted)
- [ ] Replaces image-generator-fsm `start-system.sh` as validation

## Alternatives Considered

1. **Keep per-project scripts** — Status quo. Works but 93% duplication across projects. Each new project copies and adapts, inevitably introducing drift.
2. **Docker Compose** — Handles process lifecycle but adds container overhead. Doesn't know about validation, diagrams, or event sockets.
3. **Makefile targets** — Can't handle signals, PID management, or health checks.
4. **systemd units** — Linux-only, heavyweight for dev workflows.

## Migration Path

1. Ship `statemachine-system` in statemachine-engine
2. Add `statemachine-project.yaml` to yamlgraph and image-generator-fsm
3. Validate that `statemachine-system start` produces identical behavior to current scripts
4. Replace shell scripts with one-liner: `exec statemachine-system start "$@"`
5. Eventually remove the shell wrapper entirely

## Related

- yamlgraph FR-296: `.chaplain/scripts/start-system.sh` (286 lines)
- image-generator-fsm: `scripts/start-system.sh` (419 lines)
- fsm examples: `scripts/start-system.sh` (174 lines)
- Knowledge Graph trap: `framework_costume` — "FSM wearing DAG costume → if <50% nodes use core features, wrong tool"
- Knowledge Graph cure: `spec_kill` — "Cheapest bug is the one killed in the spec"
