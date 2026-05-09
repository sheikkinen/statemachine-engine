# Feature Request: Diagram API Should Resolve config_type to machine_name

**Priority:** HIGH
**Type:** Bug
**Status:** Proposed
**Effort:** 0.5 day
**Requested:** 2026-04-28

## Summary

The UI diagram API uses `config_type` (config filename stem, e.g. `watcher-dispatcher`)
to fetch diagrams, but `statemachine-diagrams` outputs to directories named after
`machine_name` (from YAML metadata, e.g. `watcher2_dispatcher`). When these differ,
the UI gets a 404.

## Value Statement

Projects can name their config files freely without being forced to match `machine_name`,
eliminating a silent coupling that causes diagram 404s.

## Problem

Three components each use a different identifier:

| Component | Uses | Example |
|-----------|------|---------|
| Engine (`config_name`) | `config_path.stem` | `watcher-dispatcher` |
| Diagrams output dir | `metadata.machine_name` | `watcher2_dispatcher` |
| UI API request | `config_type` (= `config_name`) | `watcher-dispatcher` |
| Server file lookup | URL param directly | `watcher-dispatcher` |

The server does `path.join(PROJECT_ROOT, 'docs', 'fsm-diagrams', machine_name, 'metadata.json')`
using the URL param verbatim. When `config_type != machine_name`, the path doesn't exist.

**Current engine code** (`engine.py:160`):
```python
self.config_name = config_path.stem  # "watcher-dispatcher.yaml" -> "watcher-dispatcher"
```

**Current event payload** (`engine.py:583`):
```python
"config_type": self.config_name,  # sent to UI via websocket
```

**Current diagram output** (`diagrams.py`):
```
docs/fsm-diagrams/<machine_name>/metadata.json   # uses YAML metadata.machine_name
```

## Proposed Solution

Add a resolution layer in the server that maps `config_type` to the actual diagram
directory name. Two approaches (pick one):

### Option A: Server-side lookup (preferred)

Scan `docs/fsm-diagrams/*/metadata.json` on startup, build a map of
`config_type → directory`. When a request comes in for an unknown directory name,
check the map.

```javascript
// server.cjs - build on startup
const diagramAliases = new Map();
const diagramsRoot = path.join(PROJECT_ROOT, 'docs', 'fsm-diagrams');
if (fs.existsSync(diagramsRoot)) {
    for (const dir of fs.readdirSync(diagramsRoot)) {
        const metaPath = path.join(diagramsRoot, dir, 'metadata.json');
        if (fs.existsSync(metaPath)) {
            diagramAliases.set(dir, dir); // machine_name -> dir (identity)
            // Could also index by config_type if stored in metadata
        }
    }
}

// In route handler, resolve alias:
function resolveDiagramDir(name) {
    if (fs.existsSync(path.join(diagramsRoot, name))) return name;
    // Try common transforms: kebab-case -> snake_case
    const snaked = name.replace(/-/g, '_');
    if (fs.existsSync(path.join(diagramsRoot, snaked))) return snaked;
    return name; // fall through to 404
}
```

### Option B: Store config_type in metadata.json

`statemachine-diagrams` already writes `metadata.json`. Add a `config_aliases` field:

```json
{
    "machine_name": "watcher2_dispatcher",
    "config_aliases": ["watcher-dispatcher"],
    "diagrams": { ... }
}
```

Server indexes aliases on startup.

### Option C: Diagrams output uses config filename

Pass `--config-name` to `statemachine-diagrams` so it can output to
`docs/fsm-diagrams/watcher-dispatcher/` instead of using `machine_name`.

## Acceptance Criteria

- [ ] UI resolves diagrams when `config_type` differs from `machine_name`
- [ ] No breaking change to existing setups where they match
- [ ] Tests for name mismatch scenario
- [ ] `metadata.json` path resolution documented

## Alternatives Considered

**Force config filenames to match machine_name:** Works as a workaround (rename
`watcher-dispatcher.yaml` to `watcher2_dispatcher.yaml`) but constrains project
naming unnecessarily. Projects should be free to name config files independently.

## Workaround

Until this is fixed, ensure `metadata.machine_name` in YAML matches the config
filename stem. E.g. rename `machine_name: watcher2_dispatcher` to
`machine_name: watcher-dispatcher` in the YAML config.

## Related

- `engine.py:160`: `config_name = config_path.stem`
- `engine.py:583`: `config_type: self.config_name` in event payload
- `server.cjs:72`: Direct path lookup using URL param
- `diagrams.py`: Output directory uses `machine_name` from YAML metadata
- FR-FSM-012: First-class state_groups (related config schema work)
