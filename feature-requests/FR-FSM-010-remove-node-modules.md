# Feature Request: Remove node_modules from Source Control

**Priority:** MEDIUM
**Type:** Enhancement
**Status:** Proposed
**Effort:** 0.25 days
**Requested:** 2026-03-14

## Summary

Remove `ui/node_modules/` from git and add to `.gitignore`. Currently pollutes the repository with ~308K lines of third-party build tooling.

## Value Statement

Contributors get a clean repository without vendored dependencies, reducing clone time, diff noise, and false positives in code analysis.

## Problem

The `src/statemachine_engine/ui/node_modules/` directory is tracked in git:

```
$ find src/statemachine_engine/ui/node_modules -name "*.py" | xargs wc -l | tail -1
  308366 total
```

This includes Python files from `node-gyp` build tools (gyp, msvs generators, xcodeproj handlers) that:
1. Inflate repository size
2. Pollute line counts and code analysis
3. Trigger false positives in grep/search
4. Are reproducible via `npm install`

## Proposed Solution

### Step 1: Add to .gitignore

```gitignore
# Node.js dependencies (reproducible via npm install)
src/statemachine_engine/ui/node_modules/
```

### Step 2: Remove from git tracking

```bash
git rm -r --cached src/statemachine_engine/ui/node_modules/
git commit -m "chore(ui): remove node_modules from source control"
```

### Step 3: Document setup

Update README.md or CLAUDE.md with:

```markdown
## UI Setup

```bash
cd src/statemachine_engine/ui
npm install
```
```

## Acceptance Criteria

- [ ] `node_modules/` added to `.gitignore`
- [ ] `node_modules/` removed from git tracking
- [ ] `npm install` documented in setup instructions
- [ ] UI still builds and runs after clone + npm install

## Alternatives Considered

1. **Keep as-is** — Convenient for immediate use, but poor git hygiene
2. **Vendor specific dependencies only** — Complex to maintain
3. **Move UI to separate repo** — Overkill for this issue

## Related

- FR-FSM-009: Face-changer remnant cleanup (semantic cleanup)
- This FR: Build artifact cleanup (structural cleanup)
