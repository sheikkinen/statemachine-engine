# TODO: Package Extraction (Milestone 4)

**Status:** Ready to start
**Prerequisites:** ✅ M3 complete (tests organized)
**Estimated:** ~200K tokens

---

## Phase 1: Repository Setup

### Task 1.1: Create Repository Structure
```bash
# Create new repository
mkdir -p ~/Documents/src/statemachine-engine
cd ~/Documents/src/statemachine-engine
git init

# Create directory structure
mkdir -p src/statemachine_engine/{core,actions/builtin,database/{models,schema},monitoring,tools,ui}
mkdir -p tests/{actions,communication,database}
mkdir -p examples/{simple_worker,controller_worker,pipeline}
mkdir -p docs
```

### Task 1.2: Create pyproject.toml
```bash
# Create package configuration
cat > pyproject.toml << 'EOF'
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "statemachine-engine"
version = "1.0.0"
description = "Event-driven state machine framework with real-time monitoring"
readme = "README.md"
license = {text = "MIT"}
authors = [{name = "Your Name", email = "your@email.com"}]
requires-python = ">=3.9"
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "PyYAML>=6.0",
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "websockets>=12.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21"]

[project.scripts]
statemachine = "statemachine_engine.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
EOF
```

### Task 1.3: Create Initial Files
```bash
# Create MIT License
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2025 Sami J P Heikkinen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

# .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
.env
venv/
EOF

# README.md (basic)
cat > README.md << 'EOF'
# State Machine Engine

Event-driven state machine framework with real-time monitoring

## Installation
```bash
pip install statemachine-engine
```

See docs/ for full documentation.
EOF
```

---

## Phase 2: Copy Source Code

### Task 2.1: Copy Core Engine (6 files)
```bash
cd ~/statemachine-engine

# Core state machine
cp ~/Documents/src/face-changer/src/state_machine/engine.py \
   src/statemachine_engine/core/engine.py

cp ~/Documents/src/face-changer/src/state_machine/action_loader.py \
   src/statemachine_engine/core/action_loader.py

cp ~/Documents/src/face-changer/src/state_machine/cli.py \
   src/statemachine_engine/cli.py

cp ~/Documents/src/face-changer/src/state_machine/health_monitor.py \
   src/statemachine_engine/core/health_monitor.py

# Create __init__.py files
touch src/statemachine_engine/__init__.py
touch src/statemachine_engine/core/__init__.py
```

### Task 2.2: Copy Action Framework (8 files)
```bash
# Base action
cp ~/Documents/src/face-changer/src/actions/base.py \
   src/statemachine_engine/actions/base.py

# Core actions
cp ~/Documents/src/face-changer/src/actions/core/bash_action.py \
   src/statemachine_engine/actions/builtin/bash_action.py

cp ~/Documents/src/face-changer/src/actions/core/log_action.py \
   src/statemachine_engine/actions/builtin/log_action.py

cp ~/Documents/src/face-changer/src/actions/core/check_database_queue_action.py \
   src/statemachine_engine/actions/builtin/check_database_queue_action.py

cp ~/Documents/src/face-changer/src/actions/core/check_events_action.py \
   src/statemachine_engine/actions/builtin/check_events_action.py

cp ~/Documents/src/face-changer/src/actions/core/check_machine_state_action.py \
   src/statemachine_engine/actions/builtin/check_machine_state_action.py

cp ~/Documents/src/face-changer/src/actions/core/clear_events_action.py \
   src/statemachine_engine/actions/builtin/clear_events_action.py

cp ~/Documents/src/face-changer/src/actions/core/send_event_action.py \
   src/statemachine_engine/actions/builtin/send_event_action.py

# Create __init__.py
touch src/statemachine_engine/actions/__init__.py
touch src/statemachine_engine/actions/builtin/__init__.py
```

### Task 2.3: Copy Database Layer (10 files)
```bash
# Database models
cp ~/Documents/src/face-changer/src/database/models/base.py \
   src/statemachine_engine/database/models/base.py

cp ~/Documents/src/face-changer/src/database/models/job.py \
   src/statemachine_engine/database/models/job.py

cp ~/Documents/src/face-changer/src/database/models/machine_event.py \
   src/statemachine_engine/database/models/machine_event.py

cp ~/Documents/src/face-changer/src/database/models/machine_state.py \
   src/statemachine_engine/database/models/machine_state.py

cp ~/Documents/src/face-changer/src/database/models/realtime_event.py \
   src/statemachine_engine/database/models/realtime_event.py

# Database schemas
mkdir -p src/statemachine_engine/database/schema
cp ~/Documents/src/face-changer/src/database/schema/generic/*.sql \
   src/statemachine_engine/database/schema/

# Database CLI
cp ~/Documents/src/face-changer/src/database/cli.py \
   src/statemachine_engine/database/cli.py

# Create __init__.py
touch src/statemachine_engine/database/__init__.py
touch src/statemachine_engine/database/models/__init__.py
```

### Task 2.4: Copy Monitoring & Tools (5 files)
```bash
# WebSocket server
cp ~/Documents/src/face-changer/src/api/websocket_server.py \
   src/statemachine_engine/monitoring/websocket_server.py

touch src/statemachine_engine/monitoring/__init__.py

# FSM generator
cp ~/Documents/src/face-changer/src/fsm_generator/cli.py \
   src/statemachine_engine/tools/cli.py

cp ~/Documents/src/face-changer/src/fsm_generator/config.py \
   src/statemachine_engine/tools/config.py

cp ~/Documents/src/face-changer/src/fsm_generator/diagrams.py \
   src/statemachine_engine/tools/diagrams.py

touch src/statemachine_engine/tools/__init__.py
```

### Task 2.5: Copy UI (directory)
```bash
# Copy entire UI directory
cp -r ~/Documents/src/face-changer/statemachine-ui-mvp/* \
      src/statemachine_engine/ui/
```

---

## Phase 3: Update Imports

### Task 3.1: Update Core Engine Imports
```bash
cd ~/statemachine-engine

# Pattern: src.state_machine → statemachine_engine.core
# Pattern: src.actions → statemachine_engine.actions
# Pattern: src.database → statemachine_engine.database

# Update engine.py
sed -i '' 's/from src\.state_machine\./from statemachine_engine.core./g' \
    src/statemachine_engine/core/engine.py

sed -i '' 's/from src\.actions/from statemachine_engine.actions/g' \
    src/statemachine_engine/core/engine.py

sed -i '' 's/from src\.database/from statemachine_engine.database/g' \
    src/statemachine_engine/core/engine.py

# Update action_loader.py
sed -i '' 's/from src\.actions/from statemachine_engine.actions/g' \
    src/statemachine_engine/core/action_loader.py

# Update cli.py
sed -i '' 's/from src\.state_machine/from statemachine_engine.core/g' \
    src/statemachine_engine/cli.py

sed -i '' 's/from src\.database/from statemachine_engine.database/g' \
    src/statemachine_engine/cli.py
```

### Task 3.2: Update Action Imports
```bash
# Update all builtin actions
for file in src/statemachine_engine/actions/builtin/*.py; do
    sed -i '' 's/from src\.actions\.base/from statemachine_engine.actions.base/g' "$file"
    sed -i '' 's/from \.\.base/from ..base/g' "$file"
    sed -i '' 's/from src\.database/from statemachine_engine.database/g' "$file"
    sed -i '' 's/from src\.state_machine/from statemachine_engine.core/g' "$file"
done
```

### Task 3.3: Update Database Imports
```bash
# Update database models
for file in src/statemachine_engine/database/models/*.py; do
    sed -i '' 's/from src\.database/from statemachine_engine.database/g' "$file"
    sed -i '' 's/from \.base/from .base/g' "$file"
done

# Update database CLI
sed -i '' 's/from src\.database/from statemachine_engine.database/g' \
    src/statemachine_engine/database/cli.py
```

### Task 3.4: Create Package Exports
```bash
# src/statemachine_engine/__init__.py
cat > src/statemachine_engine/__init__.py << 'EOF'
"""State Machine Engine - Event-driven workflow framework"""

__version__ = "1.0.0"

from .core.engine import StateMachineEngine
from .core.action_loader import ActionLoader
from .actions.base import BaseAction
from .database.models.base import Database
from .database.models.job import JobModel

__all__ = [
    "StateMachineEngine",
    "ActionLoader",
    "BaseAction",
    "Database",
    "JobModel",
]
EOF

# src/statemachine_engine/core/__init__.py
cat > src/statemachine_engine/core/__init__.py << 'EOF'
from .engine import StateMachineEngine
from .action_loader import ActionLoader

__all__ = ["StateMachineEngine", "ActionLoader"]
EOF

# src/statemachine_engine/actions/__init__.py
cat > src/statemachine_engine/actions/__init__.py << 'EOF'
from .base import BaseAction

__all__ = ["BaseAction"]
EOF

# src/statemachine_engine/database/__init__.py
cat > src/statemachine_engine/database/__init__.py << 'EOF'
from .models.base import Database
from .models.job import JobModel
from .models.machine_event import MachineEventModel
from .models.machine_state import MachineStateModel
from .models.realtime_event import RealtimeEventModel

__all__ = [
    "Database",
    "JobModel",
    "MachineEventModel",
    "MachineStateModel",
    "RealtimeEventModel",
]
EOF
```

---

## Phase 4: Copy Tests

### Task 4.1: Copy Test Files
```bash
cd ~/statemachine-engine

# Copy all engine tests
cp -r ~/Documents/src/face-changer/tests/engine/* tests/

# Copy conftest if exists
if [ -f ~/Documents/src/face-changer/tests/engine/conftest.py ]; then
    cp ~/Documents/src/face-changer/tests/engine/conftest.py tests/
fi
```

### Task 4.2: Update Test Imports
```bash
# Update all test files
for file in $(find tests -name "*.py"); do
    # Update imports
    sed -i '' 's/from src\.state_machine/from statemachine_engine.core/g' "$file"
    sed -i '' 's/from src\.actions\.core/from statemachine_engine.actions.builtin/g' "$file"
    sed -i '' 's/from src\.actions\.base/from statemachine_engine.actions/g' "$file"
    sed -i '' 's/from src\.database/from statemachine_engine.database/g' "$file"

    # Update pytest fixtures path if needed
    sed -i '' 's/tests\.engine\.conftest/tests.conftest/g' "$file"
done
```

---

## Phase 5: Validation

### Task 5.1: Install Package Locally
```bash
cd ~/statemachine-engine

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

### Task 5.2: Run Tests
```bash
# Run all tests
pytest tests/ -v

# Expected: ~42/54 tests passing (78%)
# Known failures: test_log_action.py, test_clear_events_action.py
```

### Task 5.3: Test Imports
```bash
# Verify imports work
python -c "from statemachine_engine.core import StateMachineEngine; print('OK')"
python -c "from statemachine_engine.actions import BaseAction; print('OK')"
python -c "from statemachine_engine.database import JobModel; print('OK')"
```

### Task 5.4: Build Package
```bash
# Build distribution
python -m build

# Check package
twine check dist/*

# List package contents
tar -tzf dist/statemachine_engine-1.0.0.tar.gz | head -30
```

---

## Phase 6: Create Examples

### Task 6.1: Simple Worker Example
```bash
cd ~/statemachine-engine/examples/simple_worker

# Create config
cat > config/worker.yaml << 'EOF'
name: "Simple Worker"
initial_state: waiting

states:
  - waiting
  - processing
  - completed

events:
  - new_job
  - job_done

transitions:
  - from: waiting
    to: processing
    event: new_job
    actions:
      - type: check_database_queue
        params:
          job_type: task

  - from: processing
    to: completed
    event: job_done
    actions:
      - type: bash
        params:
          command: "echo Processed {job_id}"
          success: job_done
EOF

# Create README
cat > README.md << 'EOF'
# Simple Worker Example

## Run
```bash
statemachine config/worker.yaml --machine-name worker
```
EOF
```

### Task 6.2: Controller/Worker Example
```bash
cd ~/statemachine-engine/examples/controller_worker

# Create controller.yaml
cat > config/controller.yaml << 'EOF'
name: "Task Controller"
initial_state: monitoring

transitions:
  - from: monitoring
    to: monitoring
    event: task_completed
    actions:
      - type: bash
        params:
          command: "echo Job {payload.job_id} completed"
EOF

# Create worker.yaml
cat > config/worker.yaml << 'EOF'
name: "Task Worker"
initial_state: waiting

transitions:
  - from: processing
    to: notifying
    event: job_done
    actions:
      - type: send_event
        params:
          target: controller
          event_type: task_completed
EOF

# Create run.sh
cat > run.sh << 'EOF'
#!/bin/bash
statemachine config/controller.yaml --machine-name controller &
statemachine config/worker.yaml --machine-name worker &
wait
EOF
chmod +x run.sh
```

---

## Phase 7: Documentation

### Task 7.1: Create README.md
```bash
cd ~/statemachine-engine

cat > README.md << 'EOF'
# State Machine Engine

Event-driven state machine framework with real-time monitoring

## Features
- YAML-based workflow configuration
- Pluggable action system
- Real-time WebSocket monitoring
- Database-backed job queue
- Unix socket communication
- FSM diagram generation

## Installation
```bash
pip install statemachine-engine
```

## Quickstart

Create a simple worker:

```yaml
# config/worker.yaml
name: "Task Worker"
initial_state: waiting

states:
  - waiting
  - processing
  - completed

events:
  - new_job
  - job_done

transitions:
  - from: waiting
    to: processing
    event: new_job
    actions:
      - type: check_database_queue

  - from: processing
    to: completed
    event: job_done
    actions:
      - type: bash
        params:
          command: "echo Done"
          success: job_done
```

Run it:
```bash
statemachine config/worker.yaml --machine-name worker
```

## Documentation
- [Architecture](docs/architecture.md)
- [Examples](examples/)

## License
MIT
EOF
```

### Task 7.2: Create docs/quickstart.md
```bash
mkdir -p docs
cat > docs/quickstart.md << 'EOF'
# Quickstart Guide

## Installation
```bash
pip install statemachine-engine
```

## Your First State Machine

[Include simple worker example with explanation]

## Custom Actions

[Show how to create custom action]

## Multi-Machine Setup

[Show controller + worker pattern]
EOF
```

---

## Phase 8: Git & Release

### Task 8.1: Initial Commit
```bash
cd ~/statemachine-engine

git add .
git commit -m "Initial commit - state machine engine extraction

- Core engine (StateMachineEngine, ActionLoader)
- 7 builtin actions (bash, log, events, queue)
- Database models (job, machine_event, machine_state, realtime_event)
- WebSocket monitoring server
- FSM diagram generator
- Web UI
- 54 tests (78% passing)
- Examples (simple_worker, controller_worker)

Extracted from face-changer project.
"
```

### Task 8.2: Create GitHub Repository
```bash
# Create repo on GitHub (manual)
# Then:
git remote add origin https://github.com/yourorg/statemachine-engine.git
git branch -M main
git push -u origin main
```

### Task 8.3: Tag Release
```bash
git tag -a v1.0.0 -m "Version 1.0.0 - Initial release"
git push origin v1.0.0
```

---

## Verification Checklist

- [ ] Repository created with correct structure
- [ ] All 23 source files copied
- [ ] All 54 test files copied
- [ ] Imports updated (no `src.` references)
- [ ] Package exports defined (__init__.py files)
- [ ] Local install works: `pip install -e .`
- [ ] Tests run: `pytest tests/`
- [ ] Imports work: `from statemachine_engine.core import StateMachineEngine`
- [ ] Package builds: `python -m build`
- [ ] Examples created (2 working examples)
- [ ] Documentation written (README + quickstart)
- [ ] Git repository initialized
- [ ] Initial commit created
- [ ] GitHub repository created
- [ ] Release tagged

---

## File Counts

**Source Files:** 23 Python files + UI files
- Core: 4 files (engine.py, action_loader.py, cli.py, health_monitor.py)
- Actions: 8 files (base.py + 7 builtin)
- Database: 10 files (5 models + 4 schemas + cli.py)
- Monitoring: 1 file (websocket_server.py)
- Tools: 3 files (FSM generator)
- UI: ~20 files (HTML, JS, CSS)

**Test Files:** 54 tests in ~15 files
- Actions: 24 tests
- Communication: 14 tests
- Database: 2 tests
- Other: 14 tests

**Documentation:** 4+ files
- README.md
- docs/quickstart.md
- examples/*/README.md (2)

**Total Estimated:** ~200K tokens

---

## Next: Milestone 5 (Face-Changer Integration)

After M4 complete, see [plan-barebones-separation-of-concerns.md](plan-barebones-separation-of-concerns.md) for M5 details.
