# Separation of Concerns - Barebones Implementation Guide

**Date:** October 6, 2025
**Status:** Ready for Execution
**Progress:** 33% (2 of 6 milestones complete)

---

## Executive Summary

This guide provides a **step-by-step implementation plan** for extracting the generic state machine engine from face-changer into a standalone `statemachine-engine` package. The codebase is architecturally ready - this is primarily an organizational task (file moves, import updates).

**Completed:**
- ✅ Milestone 1: Database modular structure (9 files)
- ✅ Milestone 2: Jobs table simplified with JSON

**Remaining:**
- 🔜 Milestone 3: Test separation (~150K tokens)
- ⏳ Milestone 4: Package extraction (~200K tokens)
- ⏳ Milestone 5: Face-changer integration (~120K tokens)
- ⏳ Milestone 6: Public release (~250K tokens)

**Total Estimated:** ~720K tokens (~6-8 Claude sessions)

---

## Part 1: Actual Separation Implementation

### Milestone 3: Test Separation (~150K tokens)

**Goal:** Split 40 mixed test files into engine/domain/integration directories

**Token Breakdown:**
- Audit & categorization: ~30K tokens (read all test files, create classification matrix)
- Directory creation & fixture splitting: ~20K tokens
- Test file moves & import updates: ~80K tokens (40 files × ~2K per file)
- Validation & fixes: ~20K tokens

#### Task 3.1: Audit All Tests (~30K tokens)

**Input Analysis:**
```python
# Read and categorize all test files
tests/
├── test_*.py              # 40 files to classify
├── conftest.py            # Shared fixtures to analyze
├── end_to_end/            # Integration tests
└── scripts/               # Script tests
```

**Classification Criteria:**

**Engine Tests (→ will move to engine package):**
- Tests for `src/state_machine/` (engine.py, action_loader.py)
- Tests for `src/actions/core/` (7 builtin actions)
- Tests for `src/database/models/` (generic models only)
- Tests for `src/api/websocket_server.py`
- Tests for `src/fsm_generator/`

**Domain Tests (→ stays in face-changer):**
- Tests for `src/actions/domain/` (AI, ideator, job_management, pipeline)
- Tests for `src/database/models/domain/` (domain models)
- Tests for shell scripts (218 tests in 19 files)
- Tests using Anthropic/LangChain mocks
- Tests requiring test images/fixtures

**Integration Tests (→ stays in face-changer):**
- End-to-end concurrent machine tests
- Full pipeline tests
- Shell script integration tests

**Output: Classification Matrix**
```markdown
| Test File | Category | Reason | Dependencies |
|-----------|----------|--------|--------------|
| test_walking_skeleton.py | Engine | Tests database queue | - |
| test_enhance_prompt.py | Domain | Uses Anthropic API | anthropic |
| test_bash_action.py | Engine | Tests core action | - |
| test_image_crop.py | Domain | Shell script test | ImageMagick |
| ... | ... | ... | ... |
```

**Prompt:**
```
Analyze all 40 test files in tests/ directory.
For each file:
1. Read test file
2. Identify imports (what modules it tests)
3. Identify external dependencies (APIs, tools)
4. Classify as: engine, domain, or integration
5. List fixture requirements

Create classification matrix as markdown table.
```

#### Task 3.2: Create Directory Structure (~20K tokens)

**Target Structure:**
```
tests/
├── conftest.py                # Shared base fixtures
├── engine/                    # → 41 engine tests
│   ├── conftest.py           # Generic fixtures
│   ├── test_engine.py
│   ├── test_action_loader.py
│   ├── test_control_socket.py
│   ├── test_realtime_integration.py
│   ├── actions/
│   │   ├── test_bash_action.py
│   │   ├── test_log_action.py
│   │   ├── test_check_events_action.py
│   │   ├── test_clear_events_action.py
│   │   └── test_check_machine_state.py
│   └── database/
│       └── test_job_model.py
├── domain/                    # → 242 domain tests
│   ├── conftest.py           # Domain fixtures
│   ├── actions/
│   │   ├── test_enhance_prompt_action.py
│   │   ├── test_descriptor_actions.py
│   │   └── test_send_event_descriptor.py
│   ├── machines/
│   │   └── test_sdxl_generator_integration.py
│   └── scripts/              # 218 script tests
│       ├── test_coordinate_extraction.py
│       ├── test_image_crop.py
│       └── ... (17 more files)
└── integration/               # → 5 pytest + 6 shell
    ├── conftest.py
    ├── test_face_changer_pipeline.py
    ├── test_pony_flux_workflow.py
    └── shell/
        ├── e2e-concurrent.sh
        ├── e2e-face-changer.sh
        └── e2e-pony-flux.sh
```

**Fixture Separation:**

**Generic Fixtures (`tests/engine/conftest.py`):**
```python
@pytest.fixture
def temp_db():
    """Temporary SQLite database"""

@pytest.fixture
def mock_yaml_config():
    """Mock YAML state machine config"""

@pytest.fixture
def mock_context():
    """Mock execution context"""
```

**Domain Fixtures (`tests/domain/conftest.py`):**
```python
@pytest.fixture
def mock_anthropic():
    """Mock Anthropic API client"""

@pytest.fixture
def test_image():
    """Test image fixture"""

@pytest.fixture
def mock_forge_api():
    """Mock Forge API responses"""
```

**Prompts:**
```
1. Create tests/engine/conftest.py with generic fixtures (database, temp dirs, mock configs)
2. Create tests/domain/conftest.py with domain fixtures (mock APIs, test images)
3. Create tests/integration/conftest.py with integration fixtures
4. Update root conftest.py to be minimal (pytest config only)
```

#### Task 3.3: Move & Update Tests (~80K tokens)

**Process per test file:**
1. Read current test file
2. Identify fixture dependencies
3. Move to appropriate directory
4. Update imports
5. Verify pytest discovery works

**Import Update Pattern:**
```python
# BEFORE (relative imports)
from src.state_machine.engine import StateMachineEngine
from src.actions.base import BaseAction
from ..conftest import temp_db

# AFTER (engine tests use absolute imports)
from statemachine_engine.core import StateMachineEngine
from statemachine_engine.actions import BaseAction
from tests.engine.conftest import temp_db

# AFTER (domain tests keep current imports)
from src.actions.domain.ai.enhance_prompt_action import EnhancePromptAction
from tests.domain.conftest import mock_anthropic
```

**Batch Operations:**
- Move 41 engine tests: ~41 files × 1K tokens = 41K tokens
- Move 242 domain tests: ~19 files × 1.5K tokens = 28.5K tokens (many are grouped)
- Update imports: ~10K tokens

**Prompt per batch:**
```
Move the following test files to tests/engine/:
- test_engine.py
- test_action_loader.py
- test_bash_action.py
...

For each file:
1. Update imports (src.* → statemachine_engine.*)
2. Update fixture imports
3. Verify pytest can discover tests
```

#### Task 3.4: Validation (~20K tokens)

**Test Execution:**
```bash
# Run engine tests independently
pytest tests/engine/ -v --tb=short

# Run domain tests independently
pytest tests/domain/ -v --tb=short

# Run integration tests
pytest tests/integration/ -v --tb=short

# Run all tests
pytest tests/ -v
```

**Expected Results:**
- Engine: 41 tests passing (95%+ pass rate acceptable)
- Domain: 242 tests passing (90%+ pass rate acceptable)
- Integration: 5 pytest + 6 shell (manual execution)

**Fix Failures:**
- Import errors: Update import paths
- Fixture errors: Move fixture definitions
- API mocking: Update mock paths

**Prompt:**
```
Run pytest tests/engine/ and analyze failures.
For each failure:
1. Identify root cause
2. Fix import/fixture issue
3. Re-run test
4. Confirm passing
```

---

### Milestone 4: Package Extraction (~200K tokens)

**Goal:** Create standalone `statemachine-engine` repository with all generic components

**Token Breakdown:**
- Repository setup: ~10K tokens
- File copying & restructuring: ~100K tokens
- Import updates: ~50K tokens
- Documentation: ~40K tokens

#### Task 4.1: Create Repository Structure (~10K tokens)

**Commands:**
```bash
# Create new repo
mkdir statemachine-engine
cd statemachine-engine
git init

# Create directory structure
mkdir -p src/statemachine_engine/{core,actions,database,monitoring,tools,ui}
mkdir -p tests examples docs
```

**Create `pyproject.toml`:**
```toml
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "statemachine-engine"
version = "1.0.0"
description = "Event-driven state machine framework with real-time monitoring"
authors = [{name = "Your Name", email = "your@email.com"}]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.9"
keywords = ["state-machine", "workflow", "event-driven", "asyncio"]
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
]

dependencies = [
    "PyYAML>=6.0",
    "fastapi>=0.104.0",
    "uvicorn>=0.24.0",
    "websockets>=12.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
]

[project.scripts]
statemachine = "statemachine_engine.cli:main"
statemachine-ui = "statemachine_engine.ui.server:main"
statemachine-fsm = "statemachine_engine.tools.cli:main"

[project.urls]
Homepage = "https://github.com/yourorg/statemachine-engine"
Documentation = "https://statemachine-engine.readthedocs.io"
Repository = "https://github.com/yourorg/statemachine-engine"
Issues = "https://github.com/yourorg/statemachine-engine/issues"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

**Prompt:**
```
Create statemachine-engine repository with:
1. Directory structure (src/, tests/, examples/, docs/)
2. pyproject.toml with package metadata
3. Initial README.md
4. LICENSE (MIT)
5. .gitignore
```

#### Task 4.2: Copy Generic Components (~100K tokens)

**Copy Mapping:**
```
face-changer/                           → statemachine-engine/

# Core engine
src/state_machine/engine.py            → src/statemachine_engine/core/engine.py
src/state_machine/action_loader.py     → src/statemachine_engine/core/action_loader.py
src/state_machine/cli.py               → src/statemachine_engine/cli.py

# Action framework
src/actions/base.py                    → src/statemachine_engine/actions/base.py
src/actions/cli.py                     → src/statemachine_engine/actions/cli.py
src/actions/core/                      → src/statemachine_engine/actions/builtin/
  ├── bash_action.py                   →   ├── bash_action.py
  ├── log_action.py                    →   ├── log_action.py
  ├── check_database_queue_action.py   →   ├── check_database_queue_action.py
  ├── check_events_action.py           →   ├── check_events_action.py
  ├── check_machine_state_action.py    →   ├── check_machine_state_action.py
  ├── clear_events_action.py           →   ├── clear_events_action.py
  └── send_event_action.py             →   └── send_event_action.py

# Database layer
src/database/models/base.py            → src/statemachine_engine/database/models/base.py
src/database/models/job.py             → src/statemachine_engine/database/models/job.py
src/database/models/machine_event.py   → src/statemachine_engine/database/models/machine_event.py
src/database/models/machine_state.py   → src/statemachine_engine/database/models/machine_state.py
src/database/models/realtime_event.py  → src/statemachine_engine/database/models/realtime_event.py
src/database/cli.py                    → src/statemachine_engine/database/cli.py
src/database/schema/generic/           → src/statemachine_engine/database/schema/
  ├── 001_jobs.sql                     →   ├── 001_jobs.sql
  ├── 002_machine_events.sql           →   ├── 002_machine_events.sql
  ├── 003_machine_state.sql            →   ├── 003_machine_state.sql
  └── 004_realtime_events.sql          →   └── 004_realtime_events.sql

# Monitoring
src/api/websocket_server.py            → src/statemachine_engine/monitoring/websocket_server.py

# Tools
src/fsm_generator/                     → src/statemachine_engine/tools/
  ├── cli.py                           →   ├── cli.py
  ├── config.py                        →   ├── config.py
  └── diagrams.py                      →   └── diagrams.py

# UI
statemachine-ui-mvp/                   → src/statemachine_engine/ui/
  ├── server.js                        →   ├── server.js
  ├── package.json                     →   ├── package.json
  └── public/                          →   └── public/
      ├── index.html                   →       ├── index.html
      ├── app-modular.js               →       ├── app.js
      ├── style.css                    →       ├── style.css
      └── modules/                     →       └── modules/

# Tests
tests/engine/                          → tests/
  ├── conftest.py                      →   ├── conftest.py
  ├── test_engine.py                   →   ├── test_engine.py
  └── ...                              →   └── ...
```

**Token Estimate:** ~2K per file × 50 files = 100K tokens

**Prompt per batch:**
```
Copy the following files from face-changer to statemachine-engine:

Batch 1 - Core Engine:
- src/state_machine/engine.py → src/statemachine_engine/core/engine.py
- src/state_machine/action_loader.py → src/statemachine_engine/core/action_loader.py
- src/state_machine/cli.py → src/statemachine_engine/cli.py

For each file:
1. Copy file content
2. Update module docstrings (remove face-changer references)
3. Keep license headers
4. Don't update imports yet (next task)
```

#### Task 4.3: Update All Imports (~50K tokens)

**Import Mapping:**
```python
# Pattern 1: State machine imports
from src.state_machine.engine import StateMachineEngine
→ from statemachine_engine.core import StateMachineEngine

from src.state_machine.action_loader import ActionLoader
→ from statemachine_engine.core import ActionLoader

# Pattern 2: Action imports
from src.actions.base import BaseAction
→ from statemachine_engine.actions import BaseAction

from src.actions.core.bash_action import BashAction
→ from statemachine_engine.actions.builtin import BashAction

# Pattern 3: Database imports
from src.database.models import Database, JobModel
→ from statemachine_engine.database import Database, JobModel

from src.database.models.base import Database
→ from statemachine_engine.database.models import Database

# Pattern 4: Internal imports
from .engine import StateMachineEngine
→ from ..core import StateMachineEngine
```

**Files to Update:** ~50 Python files in engine package

**Prompt:**
```
Update imports in all statemachine-engine Python files.

For each file in src/statemachine_engine/:
1. Read file
2. Find all imports matching "src.*"
3. Replace with "statemachine_engine.*"
4. Update relative imports (.engine → ..core)
5. Verify no references to "face-changer" or "face_changer"
```

#### Task 4.4: Create Documentation (~40K tokens)

**Documentation Files:**

1. **README.md** (~10K tokens)
```markdown
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
[Complete example with code snippets]

## Documentation
- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Examples](examples/)
```

2. **docs/quickstart.md** (~8K tokens)
- Simple worker example
- Custom action creation
- Multi-machine setup

3. **docs/architecture.md** (~10K tokens)
- System overview
- Component descriptions
- Event flow diagrams

4. **docs/api.md** (~12K tokens)
- StateMachineEngine API
- BaseAction interface
- Database models
- YAML configuration reference

**Prompt:**
```
Create comprehensive documentation for statemachine-engine:

1. README.md with:
   - Feature highlights
   - Installation instructions
   - Quickstart example
   - Links to docs

2. docs/quickstart.md with:
   - Simple worker example
   - Custom action example
   - Multi-machine example

3. docs/architecture.md with:
   - Component diagram
   - Event flow explanation
   - Database schema

4. docs/api.md with:
   - StateMachineEngine class reference
   - BaseAction interface
   - Configuration YAML format
```

---

### Milestone 5: Face-Changer Integration (~120K tokens)

**Goal:** Update face-changer to use engine package as dependency

**Token Breakdown:**
- Install engine & update requirements: ~5K tokens
- Remove duplicated code: ~10K tokens
- Update imports: ~80K tokens (~50 files × 1.5K per file)
- Testing & validation: ~25K tokens

#### Task 5.1: Install Engine Package (~5K tokens)

**Update `requirements.txt`:**
```diff
+ # Engine dependency
+ statemachine-engine>=1.0.0

- # Now provided by engine:
- PyYAML>=6.0
- fastapi>=0.104.0
- uvicorn>=0.24.0
- websockets>=12.0

# Keep domain dependencies:
anthropic>=0.18.0
langchain>=0.1.0
langchain-anthropic>=0.1.0
pillow>=10.0.0
requests>=2.31.0
```

**Install:**
```bash
# Development (local engine package)
pip install -e ../statemachine-engine

# OR production (from PyPI)
pip install statemachine-engine>=1.0.0
```

#### Task 5.2: Remove Duplicated Code (~10K tokens)

**Delete These Directories:**
```bash
# These are now in engine package
rm -rf src/state_machine/
rm -rf src/actions/core/
rm -rf src/actions/base.py
rm -rf src/actions/cli.py
rm -rf src/database/models/base.py
rm -rf src/database/models/job.py
rm -rf src/database/models/machine_event.py
rm -rf src/database/models/machine_state.py
rm -rf src/database/models/realtime_event.py
rm -rf src/database/schema/generic/
rm -rf src/api/websocket_server.py
rm -rf src/fsm_generator/
rm -rf statemachine-ui-mvp/
```

**Keep These (Domain-Specific):**
```
src/
├── actions/domain/              # ✅ Keep
│   ├── ai/
│   ├── ideator/
│   ├── job_management/
│   └── pipeline/
├── database/
│   ├── models/domain/           # ✅ Keep
│   │   ├── controller_log.py
│   │   ├── ideation.py
│   │   ├── pipeline_result.py
│   │   └── pipeline_state.py
│   └── schema/domain/           # ✅ Keep
│       ├── 101_pipeline_results.sql
│       ├── 102_pipeline_state.sql
│       └── 103_controller_log.sql
scripts/                         # ✅ Keep
config/                          # ✅ Keep
tests/domain/                    # ✅ Keep
tests/integration/               # ✅ Keep
```

**Prompt:**
```
Remove duplicated code from face-changer that now exists in statemachine-engine:
1. List all directories/files to delete
2. Confirm each deletion
3. Update .gitignore to ignore removed paths
4. Verify git status shows clean deletions
```

#### Task 5.3: Update All Imports (~80K tokens)

**Files to Update:** ~50 Python files in face-changer

**Import Update Patterns:**
```python
# Pattern 1: Engine imports
OLD: from src.state_machine.engine import StateMachineEngine
NEW: from statemachine_engine.core import StateMachineEngine

OLD: from src.state_machine.action_loader import ActionLoader
NEW: from statemachine_engine.core import ActionLoader

# Pattern 2: Action framework
OLD: from src.actions.base import BaseAction
NEW: from statemachine_engine.actions import BaseAction

OLD: from src.actions.cli import ActionCLI
NEW: from statemachine_engine.actions import ActionCLI

# Pattern 3: Database models (generic only)
OLD: from src.database.models import Database, JobModel
NEW: from statemachine_engine.database import Database, JobModel

# Pattern 4: Domain models (no change)
KEEP: from src.database.models.domain.pipeline_result import PipelineResultModel
KEEP: from src.database.models.domain.controller_log import ControllerLogModel

# Pattern 5: Schema paths in Database init
OLD: schema_dirs=['src/database/schema/generic', 'src/database/schema/domain']
NEW: schema_dirs=['src/database/schema/domain']  # Generic now in engine
```

**Files Requiring Updates:**

1. **Domain Actions (10 files):**
   - `src/actions/domain/ai/enhance_prompt_action.py`
   - `src/actions/domain/ai/generate_image_description_action.py`
   - `src/actions/domain/ideator/*.py` (5 files)
   - `src/actions/domain/job_management/*.py` (2 files)
   - `src/actions/domain/pipeline/append_prompts_action.py`

2. **Domain Models (4 files):**
   - `src/database/models/domain/*.py` (imports from base models)

3. **CLI Scripts (3 files):**
   - `add-job.sh` (no Python imports, unchanged)
   - `demo.py`
   - Entry point scripts

4. **Test Files (~242 domain tests):**
   - `tests/domain/**/*.py` (need to update engine imports)

**Prompt per batch:**
```
Update imports in face-changer domain actions:

Batch 1 - AI Actions:
- src/actions/domain/ai/enhance_prompt_action.py
- src/actions/domain/ai/generate_image_description_action.py

For each file:
1. Read file
2. Find imports from "src.state_machine.*" → replace with "statemachine_engine.core.*"
3. Find imports from "src.actions.base" → replace with "statemachine_engine.actions"
4. Find imports from "src.database.models" (generic) → replace with "statemachine_engine.database"
5. Keep imports from "src.database.models.domain" unchanged
6. Verify syntax with python -m py_compile
```

#### Task 5.4: Testing & Validation (~25K tokens)

**Test Execution:**
```bash
# Run domain tests
pytest tests/domain/ -v --tb=short

# Run integration tests
pytest tests/integration/ -v --tb=short

# Run all tests
pytest tests/ -v

# Manual E2E test
./scripts/start-realtime.sh
./add-job.sh --type sdxl_generation --pony-prompt "test" --flux-prompt "test"
# Verify all 4 machines work correctly
```

**Expected Results:**
- Domain tests: 242 tests, 90%+ pass rate
- Integration tests: 5 tests, 80%+ pass rate
- E2E test: All 4 machines running, job completes successfully

**Fix Import Errors:**
```python
# Common error pattern:
ModuleNotFoundError: No module named 'src.state_machine'

# Fix:
from src.state_machine.engine import StateMachineEngine
→ from statemachine_engine.core import StateMachineEngine
```

**Prompt:**
```
Run pytest tests/domain/ and fix all import errors:
1. Identify failed tests
2. For each failure:
   - Read error traceback
   - Identify missing import
   - Update import path (src.* → statemachine_engine.*)
   - Re-run test
3. Continue until all tests pass
```

---

### Milestone 6: Public Release (~250K tokens)

**Goal:** Publish engine package to PyPI and announce to community

**Token Breakdown:**
- Package publishing: ~30K tokens
- Documentation website: ~80K tokens
- Example workflows: ~60K tokens
- Marketing materials: ~80K tokens

#### Task 6.1: Package Publishing (~30K tokens)

**Pre-Publish Checklist:**
```bash
# 1. Version check
grep version pyproject.toml  # Should be 1.0.0

# 2. Build package
python -m build

# 3. Check package
twine check dist/*

# 4. Test install
pip install dist/statemachine_engine-1.0.0-py3-none-any.whl

# 5. Test imports
python -c "from statemachine_engine.core import StateMachineEngine; print('OK')"

# 6. Run test suite
pytest tests/ -v
```

**Publish to PyPI Test:**
```bash
# Upload to test.pypi.org
twine upload --repository testpypi dist/*

# Test install from test PyPI
pip install --index-url https://test.pypi.org/simple/ statemachine-engine

# Verify
python -c "import statemachine_engine; print(statemachine_engine.__version__)"
```

**Publish to Production PyPI:**
```bash
# Final upload
twine upload dist/*

# Verify
pip install statemachine-engine
python -c "from statemachine_engine.core import StateMachineEngine; print('Production ready!')"
```

**Prompt:**
```
Prepare statemachine-engine for PyPI publication:
1. Review pyproject.toml (version, dependencies, classifiers)
2. Build package: python -m build
3. Check package: twine check dist/*
4. Publish to test.pypi.org
5. Test install from test PyPI
6. Publish to production PyPI
7. Verify production install
```

#### Task 6.2: Example Workflows (~60K tokens)

**Create 3 Complete Examples:**

**Example 1: Simple Worker (~15K tokens)**
```
examples/simple_worker/
├── README.md                   # Quickstart guide
├── config/
│   └── worker.yaml            # Basic state machine
├── requirements.txt
└── run.sh                     # Startup script
```

**Example 2: Controller/Worker Pattern (~20K tokens)**
```
examples/controller_worker/
├── README.md                   # Architecture explanation
├── config/
│   ├── controller.yaml        # Monitoring machine
│   └── worker.yaml            # Task processor
├── jobs/
│   └── create_job.py          # Job creation script
├── requirements.txt
└── run.sh                     # Start both machines
```

**Example 3: Multi-Stage Pipeline (~25K tokens)**
```
examples/pipeline/
├── README.md                   # Pipeline design guide
├── config/
│   ├── generator.yaml         # Stage 1: Generate data
│   ├── processor.yaml         # Stage 2: Process data
│   └── analyzer.yaml          # Stage 3: Analyze results
├── actions/
│   └── custom_actions.py      # Domain-specific actions
├── requirements.txt
└── run.sh                     # Start all 3 machines
```

**Prompt per example:**
```
Create complete "Simple Worker" example:

1. README.md with:
   - Overview
   - Prerequisites
   - Installation steps
   - Usage instructions
   - Expected output

2. config/worker.yaml with:
   - Minimal state machine (waiting → processing → completed)
   - check_database_queue action
   - bash action for processing

3. run.sh script:
   - Setup database
   - Start state machine
   - Add sample job
   - Monitor execution

4. Test example works end-to-end
```

#### Task 6.3: Documentation Website (~80K tokens)

**Documentation Structure:**
```
docs/
├── index.md                    # Landing page (~5K)
├── getting-started/
│   ├── installation.md        # Install guide (~5K)
│   ├── quickstart.md          # First state machine (~10K)
│   └── concepts.md            # Core concepts (~8K)
├── guides/
│   ├── yaml-config.md         # YAML reference (~12K)
│   ├── custom-actions.md      # Action development (~10K)
│   ├── multi-machine.md       # Concurrent setup (~10K)
│   └── monitoring.md          # UI & WebSocket (~8K)
├── api/
│   ├── engine.md              # StateMachineEngine (~8K)
│   ├── actions.md             # BaseAction & builtins (~10K)
│   └── database.md            # Models & schema (~8K)
└── examples/
    ├── simple-worker.md       # Example 1 walkthrough (~6K)
    ├── controller-worker.md   # Example 2 walkthrough (~8K)
    └── pipeline.md            # Example 3 walkthrough (~10K)
```

**Total:** ~118K tokens (split across multiple sessions)

**Prompt per doc:**
```
Write docs/getting-started/quickstart.md:

Structure:
1. Introduction (what we'll build)
2. Prerequisites
3. Step-by-step tutorial:
   - Create project directory
   - Install statemachine-engine
   - Create YAML config
   - Create custom action (optional)
   - Run state machine
   - Add jobs
   - Monitor execution
4. Next steps (links to guides)

Style:
- Clear, concise
- Code examples for every step
- Expected output shown
- Troubleshooting tips
```

#### Task 6.4: Marketing Materials (~80K tokens)

**1. Blog Post / Announcement (~20K tokens)**
```markdown
Title: "Introducing State Machine Engine: Event-Driven Workflows Made Simple"

Sections:
- Problem statement (workflow orchestration is complex)
- Solution overview (YAML-based state machines)
- Key features (real-time monitoring, pluggable actions, database-backed)
- Example use cases (data pipelines, image processing, task orchestration)
- Getting started (code example)
- Face-changer as reference implementation
- Call to action (install, try examples, contribute)
```

**2. Feature Comparison Table (~10K tokens)**
```markdown
| Feature | State Machine Engine | Airflow | Prefect | Temporal |
|---------|---------------------|---------|---------|----------|
| YAML config | ✅ | ❌ | ❌ | ❌ |
| Real-time UI | ✅ | ✅ | ✅ | ✅ |
| Embedded | ✅ | ❌ | ❌ | ❌ |
| WebSocket | ✅ | ❌ | ❌ | ❌ |
| Unix sockets | ✅ | ❌ | ❌ | ❌ |
| FSM diagrams | ✅ | ❌ | ❌ | ❌ |
| Setup time | 5 min | 1 hour | 30 min | 1 hour |
```

**3. Demo Video Script (~15K tokens)**
```
Scene 1: Introduction (30 sec)
- Show terminal, empty project directory
- Voiceover: "Let's build a state machine in 5 minutes"

Scene 2: Installation (30 sec)
- `pip install statemachine-engine`
- Show successful install

Scene 3: Create Config (90 sec)
- Create config/worker.yaml
- Explain states, events, transitions
- Show YAML syntax highlighting

Scene 4: Run Machine (60 sec)
- `statemachine config/worker.yaml`
- Show machine starting, logs
- Open UI in browser

Scene 5: Add Jobs (60 sec)
- `statemachine-cli add-job --type task`
- Show job processing in real-time
- Show state transitions in UI

Scene 6: Wrap-up (30 sec)
- Recap: YAML → State Machine → Real-time UI
- Call to action: Try examples, read docs
```

**4. Reddit/HN Post (~10K tokens)**
```markdown
Title: "I built a YAML-based state machine engine with real-time monitoring"

Body:
- Brief intro (why I built this)
- Key differentiator (YAML config + real-time UI)
- Face-changer as real-world example
- Link to GitHub + docs
- Ask for feedback

Expected engagement:
- HN: 50-100 upvotes, 20-30 comments
- r/Python: 100-200 upvotes, 30-50 comments
```

**5. GitHub README Badges (~5K tokens)**
```markdown
![PyPI](https://img.shields.io/pypi/v/statemachine-engine)
![Python](https://img.shields.io/pypi/pyversions/statemachine-engine)
![License](https://img.shields.io/github/license/yourorg/statemachine-engine)
![Tests](https://github.com/yourorg/statemachine-engine/actions/workflows/test.yml/badge.svg)
![Coverage](https://codecov.io/gh/yourorg/statemachine-engine/branch/main/graph/badge.svg)
```

**Prompt:**
```
Write announcement blog post for statemachine-engine:

Structure:
1. Hook: "Workflow orchestration doesn't have to be complex"
2. Problem: Current tools (Airflow, Prefect) are heavyweight
3. Solution: YAML-based state machines with real-time monitoring
4. Demo: Show 10-line YAML config creating working workflow
5. Features: Real-time UI, pluggable actions, Unix sockets, FSM diagrams
6. Real-world example: Face-changer (4-machine concurrent architecture)
7. Getting started: Install command, link to quickstart
8. Call to action: Star repo, try examples, contribute

Tone: Technical but accessible, show code, be concise (~800 words)
```

---

## Part 2: Using Engine in NEW Projects

### Template Project Structure

```
my-workflow/
├── config/
│   └── workflow.yaml           # State machine config
├── my_workflow/
│   ├── __init__.py
│   └── actions/                # Custom actions (optional)
│       └── custom_action.py
├── schema/
│   └── domain/                 # Domain schema (optional)
│       └── 001_tables.sql
├── tests/
│   └── test_workflow.py
├── pyproject.toml
├── requirements.txt            # statemachine-engine>=1.0.0
└── README.md
```

### Quickstart: Minimal Workflow

**Step 1: Install**
```bash
pip install statemachine-engine
```

**Step 2: Create Config**
```yaml
# config/workflow.yaml
name: "File Processor"
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
          job_type: file_processing

  - from: processing
    to: completed
    event: job_done
    actions:
      - type: bash
        params:
          command: "echo Processing {job_id}"
          success: job_done
```

**Step 3: Run**
```bash
# Start machine
statemachine config/workflow.yaml --machine-name processor

# Add job (in another terminal)
statemachine-cli add-job --type file_processing --data '{"file": "test.txt"}'

# Monitor (open browser)
statemachine-ui
```

### Custom Actions

**Create custom action:**
```python
# my_workflow/actions/process_file_action.py
from statemachine_engine.actions import BaseAction

class ProcessFileAction(BaseAction):
    async def execute(self, context):
        file_path = context['data']['file']
        # Your processing logic
        print(f"Processing {file_path}")
        return 'job_done'
```

**Use in YAML:**
```yaml
actions:
  - type: process_file        # Auto-discovered from actions/
    params:
      input: "{data.file}"
```

---

## Part 3: Using Engine in Face-Changer (Post-Extraction)

### Current Usage (Before Extraction)

```python
# Embedded engine
from src.state_machine.engine import StateMachineEngine
from src.actions.base import BaseAction
```

### New Usage (After Extraction)

```python
# Engine as dependency
from statemachine_engine.core import StateMachineEngine
from statemachine_engine.actions import BaseAction
from statemachine_engine.database import JobModel, Database
```

### What Face-Changer Keeps

```
face-changer/
├── config/                     # ✅ YAML configs (unchanged)
│   ├── sdxl_generator.yaml
│   ├── face_processor.yaml
│   ├── controller.yaml
│   └── descriptor.yaml
├── src/face_changer/
│   ├── actions/domain/         # ✅ Domain actions
│   │   ├── ai/                 # LangChain integration
│   │   ├── ideator/            # Prompt ideation
│   │   ├── job_management/     # CRUD operations
│   │   └── pipeline/           # Workflow logic
│   └── database/
│       ├── models/domain/      # ✅ Domain models
│       │   ├── pipeline_result.py
│       │   ├── controller_log.py
│       │   └── ideation.py
│       └── schema/domain/      # ✅ Domain schemas
│           ├── 101_pipeline_results.sql
│           ├── 102_pipeline_state.sql
│           └── 103_controller_log.sql
├── scripts/                    # ✅ Bash scripts
├── tests/domain/               # ✅ Domain tests
├── tests/integration/          # ✅ Integration tests
└── requirements.txt            # + statemachine-engine>=1.0.0
```

### Running Face-Changer (Post-Extraction)

**No changes to CLI:**
```bash
# Same commands work
./scripts/start-realtime.sh
./add-job.sh --type sdxl_generation --pony-prompt "test" --flux-prompt "test"
python src/database/cli.py machine-status
```

**No changes to YAML:**
```yaml
# config/sdxl_generator.yaml (unchanged)
actions:
  - type: bash              # Built-in action (from engine)
  - type: enhance_prompt    # Domain action (from face-changer)
```

---

## Part 4: Sample Controller/Controlled Machines

### Example 1: Simple Worker

**File: `examples/simple_worker/config/worker.yaml`**
```yaml
name: "Simple Task Worker"
description: "Processes tasks from job queue"

initial_state: initializing

metadata:
  machine_name: worker
  job_type: simple_task

states:
  - initializing
  - waiting
  - processing
  - completed
  - stopped

events:
  - initialized
  - new_job
  - no_jobs
  - job_done
  - stop

transitions:
  # Initialization
  - from: initializing
    to: waiting
    event: initialized
    actions:
      - type: bash
        params:
          command: "mkdir -p data/output"
          success: initialized

  # Job checking
  - from: waiting
    to: processing
    event: new_job
    actions:
      - type: check_database_queue
        params:
          job_type: simple_task

  - from: waiting
    to: waiting
    event: no_jobs

  # Job processing
  - from: processing
    to: completed
    event: job_done
    actions:
      - type: bash
        params:
          command: "echo 'Processed {job_id}' > data/output/{job_id}.txt"
          success: job_done

  # Completion
  - from: completed
    to: waiting
    event: initialized

  # Stop
  - from: "*"
    to: stopped
    event: stop
```

**Usage:**
```bash
# Start worker
statemachine examples/simple_worker/config/worker.yaml --machine-name worker

# Add job
statemachine-cli add-job --type simple_task --data '{"message": "Hello"}'

# Verify output
cat data/output/*.txt
```

---

### Example 2: Controller + Worker Pattern

**File: `examples/controller_worker/config/worker.yaml`**
```yaml
name: "Task Worker"
description: "Worker that notifies controller upon completion"

initial_state: waiting

metadata:
  machine_name: task_worker
  job_type: task

states:
  - waiting
  - processing
  - notifying_controller
  - completed

events:
  - new_job
  - job_done
  - notification_sent

transitions:
  # Job processing
  - from: waiting
    to: processing
    event: new_job
    actions:
      - type: check_database_queue
        params:
          job_type: task

  - from: processing
    to: notifying_controller
    event: job_done
    actions:
      - type: bash
        params:
          command: "echo Processing {job_id}"
          success: job_done

  # Notify controller
  - from: notifying_controller
    to: completed
    event: notification_sent
    actions:
      - type: send_event
        params:
          target: task_controller
          event_type: task_completed
          payload:
            job_id: "{job_id}"
            result: "success"
            timestamp: "{timestamp}"

  # Reset
  - from: completed
    to: waiting
    event: new_job
```

**File: `examples/controller_worker/config/controller.yaml`**
```yaml
name: "Task Controller"
description: "Monitors worker completion and logs results"

initial_state: monitoring

metadata:
  machine_name: task_controller

states:
  - monitoring
  - handling_completion
  - logging_result

events:
  - task_completed
  - result_logged

transitions:
  # Monitor for events
  - from: monitoring
    to: handling_completion
    event: task_completed
    actions:
      - type: check_events
        params:
          event_types: ["task_completed"]

  # Handle completion
  - from: handling_completion
    to: logging_result
    event: result_logged
    actions:
      - type: bash
        params:
          command: "echo '[{timestamp}] Task {payload.job_id} completed' >> logs/controller.log"
          success: result_logged

  # Resume monitoring
  - from: logging_result
    to: monitoring
    event: result_logged
```

**Usage:**
```bash
# Terminal 1: Start controller
statemachine examples/controller_worker/config/controller.yaml \
  --machine-name task_controller

# Terminal 2: Start worker
statemachine examples/controller_worker/config/worker.yaml \
  --machine-name task_worker

# Terminal 3: Add jobs
for i in {1..5}; do
  statemachine-cli add-job --type task --data "{\"id\": $i}"
done

# Terminal 4: Monitor UI
statemachine-ui
# Open http://localhost:3001

# Verify logs
tail -f logs/controller.log
```

**Expected Output:**
```
[2025-10-06 10:00:01] Task job_001 completed
[2025-10-06 10:00:02] Task job_002 completed
[2025-10-06 10:00:03] Task job_003 completed
...
```

---

### Example 3: Multi-Stage Pipeline

**Architecture:**
```
Generator → Processor → Analyzer
    ↓           ↓           ↓
  data/     data/temp/   data/final/
```

**File: `examples/pipeline/config/generator.yaml`**
```yaml
name: "Data Generator"
initial_state: waiting

transitions:
  - from: processing
    to: notifying_processor
    event: generated
    actions:
      - type: bash
        params:
          command: "echo 'data' > data/input_{job_id}.txt"
          success: generated

  - from: notifying_processor
    to: completed
    event: notification_sent
    actions:
      - type: send_event
        params:
          target: data_processor
          event_type: data_ready
          payload:
            job_id: "{job_id}"
            file: "data/input_{job_id}.txt"
```

**File: `examples/pipeline/config/processor.yaml`**
```yaml
name: "Data Processor"
initial_state: waiting

transitions:
  - from: waiting
    to: processing
    event: data_ready
    actions:
      - type: check_events
        params:
          event_types: ["data_ready"]

  - from: processing
    to: notifying_analyzer
    event: processed
    actions:
      - type: bash
        params:
          command: "cat {payload.file} | tr '[:lower:]' '[:upper:]' > data/temp/{job_id}.txt"
          success: processed

  - from: notifying_analyzer
    to: completed
    event: notification_sent
    actions:
      - type: send_event
        params:
          target: data_analyzer
          event_type: processing_done
          payload:
            job_id: "{job_id}"
            file: "data/temp/{job_id}.txt"
```

**File: `examples/pipeline/config/analyzer.yaml`**
```yaml
name: "Data Analyzer"
initial_state: waiting

transitions:
  - from: waiting
    to: analyzing
    event: processing_done
    actions:
      - type: check_events
        params:
          event_types: ["processing_done"]

  - from: analyzing
    to: completed
    event: analyzed
    actions:
      - type: bash
        params:
          command: "wc -l {payload.file} > data/final/{job_id}_analysis.txt"
          success: analyzed
```

**Usage:**
```bash
# Start all machines (use run.sh script)
./examples/pipeline/run.sh

# Add job
statemachine-cli add-job --type data_generation

# Watch pipeline
watch -n 1 'ls -la data/ data/temp/ data/final/'

# Verify results
cat data/final/*_analysis.txt
```

---

## Part 5: Development Guide

### For Engine Contributors

**Setup Development Environment:**
```bash
# Clone repo
git clone https://github.com/yourorg/statemachine-engine
cd statemachine-engine

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linter
ruff check src/

# Generate docs
mkdocs serve
```

**Project Structure:**
```
statemachine-engine/
├── src/statemachine_engine/
│   ├── __init__.py              # Package exports
│   ├── core/                    # State machine engine
│   │   ├── engine.py            # StateMachineEngine class
│   │   └── action_loader.py    # Dynamic action loading
│   ├── actions/                 # Action framework
│   │   ├── __init__.py
│   │   ├── base.py              # BaseAction interface
│   │   └── builtin/             # Built-in actions
│   │       ├── bash_action.py
│   │       ├── log_action.py
│   │       ├── check_database_queue_action.py
│   │       ├── check_events_action.py
│   │       ├── check_machine_state_action.py
│   │       ├── clear_events_action.py
│   │       └── send_event_action.py
│   ├── database/                # Database layer
│   │   ├── models/
│   │   │   ├── base.py          # Database class
│   │   │   ├── job.py           # JobModel
│   │   │   ├── machine_event.py
│   │   │   ├── machine_state.py
│   │   │   └── realtime_event.py
│   │   ├── schema/
│   │   │   ├── 001_jobs.sql
│   │   │   ├── 002_machine_events.sql
│   │   │   ├── 003_machine_state.sql
│   │   │   └── 004_realtime_events.sql
│   │   └── cli.py               # Database CLI
│   ├── monitoring/              # WebSocket server
│   │   └── websocket_server.py
│   ├── tools/                   # FSM generator
│   │   ├── cli.py
│   │   ├── config.py
│   │   └── diagrams.py
│   └── ui/                      # Web UI
│       ├── server.js
│       ├── package.json
│       └── public/
├── tests/                       # 41 engine tests
│   ├── conftest.py
│   ├── test_engine.py
│   ├── test_action_loader.py
│   └── actions/
├── examples/                    # 3 example workflows
│   ├── simple_worker/
│   ├── controller_worker/
│   └── pipeline/
├── docs/                        # Documentation
│   ├── index.md
│   ├── getting-started/
│   ├── guides/
│   ├── api/
│   └── examples/
└── pyproject.toml
```

**Adding New Built-in Actions:**

1. **Create action file:**
```python
# src/statemachine_engine/actions/builtin/my_action.py
from ..base import BaseAction

class MyAction(BaseAction):
    """
    My custom action that does X.

    YAML Usage:
        actions:
          - type: my_action
            params:
              param1: value1
    """

    async def execute(self, context):
        param1 = self.config.get('param1')
        # Your logic here
        return 'success'
```

2. **Add tests:**
```python
# tests/actions/test_my_action.py
import pytest
from statemachine_engine.actions.builtin import MyAction

@pytest.mark.asyncio
async def test_my_action():
    action = MyAction({'param1': 'test'})
    context = {}
    result = await action.execute(context)
    assert result == 'success'
```

3. **Update documentation:**
```markdown
# docs/api/actions.md

## my_action

Description: Does X

Parameters:
- `param1` (required): Description

Example:
```yaml
actions:
  - type: my_action
    params:
      param1: "value"
```
```

4. **Submit PR:**
```bash
git checkout -b feature/my-action
git add src/statemachine_engine/actions/builtin/my_action.py
git add tests/actions/test_my_action.py
git commit -m "feat: Add my_action for X functionality"
git push origin feature/my-action
# Create PR on GitHub
```

---

### For Domain Application Developers

**Setup Project:**
```bash
# Create project
mkdir my-workflow && cd my-workflow

# Install engine
pip install statemachine-engine

# Create structure
mkdir -p config my_workflow/actions tests
touch config/workflow.yaml
touch my_workflow/__init__.py
```

**Create Domain Action:**
```python
# my_workflow/actions/process_action.py
from statemachine_engine.actions import BaseAction
import logging

logger = logging.getLogger(__name__)

class ProcessAction(BaseAction):
    """Domain-specific processing action"""

    async def execute(self, context):
        # Get job data
        job_id = context['job_id']
        data = context.get('data', {})

        logger.info(f"Processing job {job_id} with data: {data}")

        # Your domain logic here
        result = self.process_data(data)

        # Store result in context for next action
        context['result'] = result

        return 'processed'

    def process_data(self, data):
        # Domain-specific logic
        return {"status": "success"}
```

**Use in YAML:**
```yaml
# config/workflow.yaml
name: "My Workflow"
initial_state: waiting

transitions:
  - from: processing
    to: completed
    event: processed
    actions:
      - type: process        # Auto-discovered from my_workflow/actions/
        params:
          config: "value"
```

**Test Domain Action:**
```python
# tests/test_process_action.py
import pytest
from my_workflow.actions.process_action import ProcessAction

@pytest.mark.asyncio
async def test_process_action():
    action = ProcessAction({})
    context = {
        'job_id': 'test_001',
        'data': {'key': 'value'}
    }
    result = await action.execute(context)
    assert result == 'processed'
    assert 'result' in context
```

**Run Workflow:**
```bash
# Start machine
statemachine config/workflow.yaml --machine-name my_worker

# Add job
statemachine-cli add-job --type my_task --data '{"key": "value"}'

# Monitor
statemachine-ui
```

---

### Best Practices

**State Machine Design:**

1. ✅ **Use initialization states:**
```yaml
# GOOD: One-time setup separated
states:
  - initializing    # Setup
  - waiting         # Monitoring loop

initializing:
  actions:
    - type: bash
      command: "mkdir -p data/"
      success: initialized

waiting:
  actions:
    - type: check_database_queue    # No setup here!
```

```yaml
# BAD: Setup in loop (executes 360x/min)
waiting:
  actions:
    - type: bash
      command: "mkdir -p data/"    # ❌ Re-runs constantly!
    - type: check_database_queue
```

2. ✅ **Separate setup from monitoring:**
   - **Setup actions** → Transition states (run once, move to next state)
   - **Monitoring actions** → Self-loop states (run repeatedly, same state)

3. ✅ **Use explicit events:**
```yaml
# GOOD: Explicit event
- from: processing
  to: completed
  event: job_done
  actions:
    - type: bash
      success: job_done    # Explicit event emission

# BAD: Implicit transition (not supported)
- from: processing
  to: completed
  # Missing event!
```

4. ✅ **Keep actions atomic:**
```yaml
# GOOD: Single responsibility
- from: processing
  to: validated
  event: validated
  actions:
    - type: validate_input

- from: validated
  to: transformed
  event: transformed
  actions:
    - type: transform_data

# BAD: Multiple responsibilities
- from: processing
  to: completed
  event: done
  actions:
    - type: validate_input
    - type: transform_data
    - type: store_result
    # Too much in one transition!
```

**Testing:**

1. ✅ **Mock external dependencies:**
```python
@pytest.fixture
def mock_api(mocker):
    return mocker.patch('my_module.api_client')

@pytest.mark.asyncio
async def test_action_with_api(mock_api):
    mock_api.call.return_value = {"status": "ok"}
    action = MyAction({})
    result = await action.execute({})
    assert result == 'success'
```

2. ✅ **Use temporary directories:**
```python
@pytest.fixture
def temp_dir(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir

def test_file_processing(temp_dir):
    input_file = temp_dir / "input.txt"
    input_file.write_text("test")
    # Test logic
```

3. ✅ **Test state machines end-to-end:**
```python
@pytest.mark.asyncio
async def test_workflow_e2e(temp_db):
    engine = StateMachineEngine(machine_name="test")
    await engine.load_config("config/workflow.yaml")

    # Add job
    job_model = JobModel(temp_db)
    job_model.create_job(job_id="test_001", job_type="task")

    # Run engine for 5 seconds
    task = asyncio.create_task(engine.run())
    await asyncio.sleep(5)
    engine.is_running = False
    await task

    # Verify completion
    job = job_model.get_job("test_001")
    assert job['status'] == 'completed'
```

**Documentation:**

1. ✅ **Document YAML configs:**
```yaml
# config/workflow.yaml
# ============================================================================
# Worker Machine Configuration
# ============================================================================
# Purpose: Process tasks from job queue
# Job Type: task
# Dependencies: None
# ============================================================================

name: "Task Worker"
```

2. ✅ **Generate FSM diagrams:**
```bash
# Generate diagram
statemachine-fsm config/workflow.yaml

# Output: docs/fsm/workflow/
# - state-diagram.md
# - state-diagram.mmd
```

3. ✅ **Write example job payloads:**
```markdown
# README.md

## Usage

Add job:
```bash
statemachine-cli add-job --type task --data '{
  "input_file": "data/input.txt",
  "output_file": "data/output.txt",
  "options": {
    "format": "json"
  }
}'
```
```

---

## Token Budget Summary

| Milestone | Description | Token Estimate |
|-----------|-------------|----------------|
| **M3** | Test Separation | ~150K |
| **M4** | Package Extraction | ~200K |
| **M5** | Face-Changer Integration | ~120K |
| **M6** | Public Release | ~250K |
| **TOTAL** | All Milestones | **~720K** |

**Claude Sessions Needed:** 6-8 sessions (assuming 100-120K effective per session)

---

## Next Steps

**Immediate Action: Start Milestone 3**

```bash
# 1. Review this plan
# 2. Start test separation:
#    - Audit all 40 test files
#    - Create classification matrix
#    - Create directory structure
#    - Split fixtures
#    - Move tests
#    - Validate

# Estimated: ~150K tokens, 1-2 Claude sessions
```

**Checkpoint After M3:**
- All tests organized (engine/domain/integration)
- 95%+ test pass rate
- Clear separation documented
- Ready for package extraction

---

**Document Status:** Ready for execution
**Last Updated:** October 6, 2025
**Next Review:** After Milestone 3 completion
