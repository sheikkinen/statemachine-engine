# TODO: Port Face-Changer to Statemachine-Engine

**Date:** October 7, 2025  
**Status:** Planning Phase  
**Approach:** Full Reimplementation (Clean Slate)

---

## Overview

Create a new face-changer implementation using `statemachine-engine` as a library dependency. This is a **clean reimplementation**, not a migration. The engine and face-changer will maintain **separate databases** for clear separation of concerns.

**Key Principles:**
- ✅ Engine provides generic workflow infrastructure
- ✅ Face-changer provides domain-specific AI/image logic
- ✅ Separate databases: `engine.db` (jobs, events, state) + `face_changer.db` (pipeline results, metadata)
- ✅ Communication via events and shared job IDs

---

## Architecture: Two-Database Design

### Database 1: Engine Database (`data/engine.db`)

**Managed by:** `statemachine-engine` package  
**Purpose:** Generic workflow orchestration  
**Schema:** Built-in engine tables

```sql
-- Managed by engine
jobs                    -- Job queue (all job types)
machine_events          -- Inter-machine events
machine_state           -- Current state of machines
realtime_events         -- WebSocket broadcast queue
```

**Usage:**
```python
from statemachine_engine.database import get_database, get_job_model

# Engine manages this database
db = get_database('data/engine.db')
job_model = get_job_model()
```

### Database 2: Face-Changer Database (`data/face_changer.db`)

**Managed by:** Face-changer application  
**Purpose:** Domain-specific metadata and results  
**Schema:** Custom application tables

```sql
-- Managed by face-changer
pipeline_results        -- Image generation results
pipeline_state          -- Processing state per job
controller_log          -- Controller activity log
ideation_results        -- Prompt ideation data
image_metadata          -- Image analysis results
```

**Usage:**
```python
# Face-changer manages this database
from face_changer.database import FaceChangerDatabase

db = FaceChangerDatabase('data/face_changer.db')
```

### Database Interaction Pattern

```
Job Flow:
1. Job created in engine.db (jobs table)
2. Worker picks up job from engine.db
3. Worker processes and stores results in face_changer.db
4. Worker updates job status in engine.db
5. Controller reads results from face_changer.db for orchestration

Event Flow:
1. Worker completes stage → send_event to engine.db (machine_events)
2. Controller receives event from engine.db
3. Controller reads details from face_changer.db
4. Controller creates next job in engine.db
```

---

## Project Structure

```
face-changer-v2/
├── config/                              # State machine configs
│   ├── controller.yaml                  # Orchestrates workflow
│   ├── sdxl_generator.yaml             # Image generation
│   ├── face_processor.yaml             # Face processing
│   └── descriptor.yaml                  # Description generation
│
├── face_changer/                        # Python package
│   ├── __init__.py
│   ├── database/                        # Domain database
│   │   ├── __init__.py
│   │   ├── models.py                   # FaceChangerDatabase class
│   │   └── schema/
│   │       ├── 001_pipeline_results.sql
│   │       ├── 002_pipeline_state.sql
│   │       ├── 003_controller_log.sql
│   │       ├── 004_ideation_results.sql
│   │       └── 005_image_metadata.sql
│   │
│   ├── actions/                         # Custom actions
│   │   ├── __init__.py
│   │   ├── ai/                          # AI actions
│   │   │   ├── __init__.py
│   │   │   ├── enhance_prompt_action.py
│   │   │   └── generate_description_action.py
│   │   ├── ideation/                    # Prompt ideation
│   │   │   ├── __init__.py
│   │   │   ├── ideate_prompts_action.py
│   │   │   └── select_prompt_action.py
│   │   ├── pipeline/                    # Pipeline actions
│   │   │   ├── __init__.py
│   │   │   ├── initialize_pipeline_action.py
│   │   │   ├── append_prompts_action.py
│   │   │   └── finalize_pipeline_action.py
│   │   └── job_management/             # Job CRUD
│   │       ├── __init__.py
│   │       ├── create_job_action.py
│   │       └── update_job_action.py
│   │
│   └── utils/                           # Utilities
│       ├── __init__.py
│       ├── image_utils.py
│       └── api_clients.py
│
├── scripts/                             # Shell scripts
│   ├── start-system.sh                  # Start all machines
│   ├── stop-system.sh                   # Stop all
│   ├── add-job.sh                       # Create job
│   ├── image/                           # ImageMagick ops
│   │   ├── crop_face.sh
│   │   ├── verify_portrait.sh
│   │   ├── create_mask.sh
│   │   └── merge_images.sh
│   └── dev/                             # Development tools
│       ├── reset-db.sh
│       └── test-workflow.sh
│
├── data/                                # Data directory
│   ├── engine.db                        # Engine database
│   ├── face_changer.db                  # Domain database
│   ├── images/                          # Image processing
│   │   ├── 0-generated/
│   │   ├── 1-portraits/
│   │   ├── 2-verified/
│   │   ├── 3-masks/
│   │   ├── 4-results/
│   │   ├── 5-resized/
│   │   └── 6-final/
│   └── prompts/                         # Prompt library
│
├── logs/                                # Log files
│   ├── controller.log
│   ├── sdxl_generator.log
│   ├── face_processor.log
│   ├── descriptor.log
│   └── system.log
│
├── tests/                               # Test suite
│   ├── conftest.py
│   ├── test_actions/
│   ├── test_pipeline/
│   └── test_integration/
│
├── requirements.txt                     # Python dependencies
├── pyproject.toml                       # Package config
├── README.md
└── .env.example                         # API keys template
```

---

## Phase 1: Project Setup

### Task 1.1: Create Repository Structure
**Estimated:** 1 hour

```bash
# Create project
mkdir face-changer-v2 && cd face-changer-v2

# Create directories
mkdir -p config
mkdir -p face_changer/{database/schema,actions/{ai,ideation,pipeline,job_management},utils}
mkdir -p scripts/{image,dev}
mkdir -p data/{images/{0-generated,1-portraits,2-verified,3-masks,4-results,5-resized,6-final},prompts}
mkdir -p logs
mkdir -p tests/{test_actions,test_pipeline,test_integration}

# Create __init__.py files
touch face_changer/__init__.py
touch face_changer/database/__init__.py
touch face_changer/actions/__init__.py
touch face_changer/actions/{ai,ideation,pipeline,job_management}/__init__.py
touch face_changer/utils/__init__.py
touch tests/conftest.py

# Initialize git
git init
```

### Task 1.2: Create Requirements File
**Estimated:** 30 minutes

```txt
# requirements.txt

# State Machine Engine (core dependency)
statemachine-engine>=0.0.0

# AI/ML Libraries
anthropic>=0.18.0
langchain>=0.1.20
langchain-anthropic>=0.1.4

# Image Processing
pillow>=10.0.0
pillow-heif>=0.13.0

# API Clients
requests>=2.31.0
httpx>=0.25.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.5.0

# Development
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-mock>=3.12.0
black>=23.11.0
ruff>=0.1.6
```

### Task 1.3: Create Package Configuration
**Estimated:** 30 minutes

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=64", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "face-changer"
version = "2.0.0"
description = "AI-powered face image generation and processing pipeline"
authors = [{name = "Your Name", email = "your@email.com"}]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.9"

dependencies = [
    "statemachine-engine>=1.0.0",
    "anthropic>=0.18.0",
    "langchain>=0.1.20",
    "langchain-anthropic>=0.1.4",
    "pillow>=10.0.0",
    "requests>=2.31.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-mock>=3.12.0",
    "black>=23.11.0",
    "ruff>=0.1.6",
]

[project.scripts]
face-changer = "face_changer.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["face_changer*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
asyncio_mode = "auto"
```

### Task 1.4: Create Environment Template
**Estimated:** 15 minutes

```bash
# .env.example
# Copy to .env and fill in your values

# Anthropic API
ANTHROPIC_API_KEY=sk-ant-xxx

# Forge API (SDXL generation)
FORGE_API_URL=http://localhost:7860
FORGE_API_KEY=optional

# Database Paths
ENGINE_DB_PATH=data/engine.db
FACE_CHANGER_DB_PATH=data/face_changer.db

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs

# Image Processing
IMAGE_BASE_DIR=data/images
```

---

## Phase 2: Database Layer

### Task 2.1: Create Face-Changer Database Schema
**Estimated:** 2 hours

```sql
-- face_changer/database/schema/001_pipeline_results.sql
CREATE TABLE IF NOT EXISTS pipeline_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    stage TEXT NOT NULL,                    -- 'generation', 'processing', 'description'
    status TEXT NOT NULL,                   -- 'pending', 'processing', 'completed', 'failed'
    input_data TEXT,                        -- JSON input data
    output_data TEXT,                       -- JSON output data
    error_message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(job_id, stage)
);

CREATE INDEX idx_pipeline_results_job_id ON pipeline_results(job_id);
CREATE INDEX idx_pipeline_results_stage ON pipeline_results(stage);
CREATE INDEX idx_pipeline_results_status ON pipeline_results(status);
```

```sql
-- face_changer/database/schema/002_pipeline_state.sql
CREATE TABLE IF NOT EXISTS pipeline_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL UNIQUE,
    current_stage TEXT NOT NULL,            -- 'sdxl_generation', 'face_processing', etc.
    stages_completed TEXT,                  -- JSON array of completed stages
    total_stages INTEGER DEFAULT 3,
    sdxl_job_id TEXT,                      -- Reference to SDXL sub-job
    face_job_id TEXT,                      -- Reference to face processing sub-job
    descriptor_job_id TEXT,                -- Reference to descriptor sub-job
    final_image_path TEXT,
    metadata TEXT,                         -- JSON metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pipeline_state_current_stage ON pipeline_state(current_stage);
```

```sql
-- face_changer/database/schema/003_controller_log.sql
CREATE TABLE IF NOT EXISTS controller_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_name TEXT NOT NULL,
    job_id TEXT,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    level TEXT DEFAULT 'info',              -- 'debug', 'info', 'warning', 'error'
    metadata TEXT,                          -- JSON additional data
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_controller_log_job_id ON controller_log(job_id);
CREATE INDEX idx_controller_log_timestamp ON controller_log(timestamp);
CREATE INDEX idx_controller_log_level ON controller_log(level);
```

```sql
-- face_changer/database/schema/004_ideation_results.sql
CREATE TABLE IF NOT EXISTS ideation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    iteration INTEGER NOT NULL,
    prompt TEXT NOT NULL,
    enhanced_prompt TEXT,
    score REAL,
    metadata TEXT,                          -- JSON ideation data
    selected BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(job_id, iteration)
);

CREATE INDEX idx_ideation_results_job_id ON ideation_results(job_id);
CREATE INDEX idx_ideation_results_selected ON ideation_results(selected);
```

```sql
-- face_changer/database/schema/005_image_metadata.sql
CREATE TABLE IF NOT EXISTS image_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    image_path TEXT NOT NULL,
    stage TEXT NOT NULL,                    -- 'generated', 'cropped', 'verified', etc.
    width INTEGER,
    height INTEGER,
    format TEXT,
    file_size_bytes INTEGER,
    face_count INTEGER,
    face_coordinates TEXT,                  -- JSON array of face boxes
    quality_score REAL,
    metadata TEXT,                          -- JSON additional metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_image_metadata_job_id ON image_metadata(job_id);
CREATE INDEX idx_image_metadata_stage ON image_metadata(stage);
```

### Task 2.2: Create Database Model Class
**Estimated:** 2 hours

```python
# face_changer/database/models.py
"""
Face-Changer Database Models

Separate database from engine - this handles domain-specific data only.
Engine database handles generic workflow (jobs, events, state).
"""
import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class FaceChangerDatabase:
    """
    Domain-specific database for face-changer metadata and results.
    
    Separate from engine database which handles:
    - jobs (job queue)
    - machine_events (inter-machine communication)
    - machine_state (workflow state)
    - realtime_events (UI updates)
    """
    
    def __init__(self, db_path: str = "data/face_changer.db"):
        self.db_path = db_path
        self.conn = None
        self._initialize()
    
    def _initialize(self):
        """Create database and apply schema"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # Apply schema
        schema_dir = Path(__file__).parent / "schema"
        for schema_file in sorted(schema_dir.glob("*.sql")):
            with open(schema_file) as f:
                self.conn.executescript(f.read())
        
        self.conn.commit()
        logger.info(f"Face-changer database initialized: {self.db_path}")
    
    # ========== Pipeline Results ==========
    
    def create_pipeline_result(self, job_id: str, stage: str, 
                               input_data: Dict = None, status: str = "pending") -> int:
        """Create pipeline result entry"""
        cursor = self.conn.execute("""
            INSERT INTO pipeline_results (job_id, stage, status, input_data)
            VALUES (?, ?, ?, ?)
        """, (job_id, stage, status, json.dumps(input_data) if input_data else None))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_pipeline_result(self, job_id: str, stage: str,
                               status: str = None, output_data: Dict = None,
                               error_message: str = None, processing_time_ms: int = None):
        """Update pipeline result"""
        updates = []
        values = []
        
        if status:
            updates.append("status = ?")
            values.append(status)
        if output_data:
            updates.append("output_data = ?")
            values.append(json.dumps(output_data))
        if error_message:
            updates.append("error_message = ?")
            values.append(error_message)
        if processing_time_ms:
            updates.append("processing_time_ms = ?")
            values.append(processing_time_ms)
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.extend([job_id, stage])
        
        self.conn.execute(f"""
            UPDATE pipeline_results 
            SET {', '.join(updates)}
            WHERE job_id = ? AND stage = ?
        """, values)
        self.conn.commit()
    
    def get_pipeline_result(self, job_id: str, stage: str) -> Optional[Dict]:
        """Get pipeline result for specific stage"""
        cursor = self.conn.execute("""
            SELECT * FROM pipeline_results WHERE job_id = ? AND stage = ?
        """, (job_id, stage))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # ========== Pipeline State ==========
    
    def create_pipeline_state(self, job_id: str, current_stage: str) -> int:
        """Initialize pipeline state"""
        cursor = self.conn.execute("""
            INSERT INTO pipeline_state (job_id, current_stage, stages_completed)
            VALUES (?, ?, '[]')
        """, (job_id, current_stage))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_pipeline_state(self, job_id: str, **kwargs):
        """Update pipeline state fields"""
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in ['current_stage', 'sdxl_job_id', 'face_job_id', 
                      'descriptor_job_id', 'final_image_path']:
                updates.append(f"{key} = ?")
                values.append(value)
            elif key in ['stages_completed', 'metadata']:
                updates.append(f"{key} = ?")
                values.append(json.dumps(value))
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(job_id)
        
        self.conn.execute(f"""
            UPDATE pipeline_state 
            SET {', '.join(updates)}
            WHERE job_id = ?
        """, values)
        self.conn.commit()
    
    def get_pipeline_state(self, job_id: str) -> Optional[Dict]:
        """Get pipeline state"""
        cursor = self.conn.execute("""
            SELECT * FROM pipeline_state WHERE job_id = ?
        """, (job_id,))
        row = cursor.fetchone()
        if row:
            state = dict(row)
            state['stages_completed'] = json.loads(state['stages_completed'])
            if state['metadata']:
                state['metadata'] = json.loads(state['metadata'])
            return state
        return None
    
    # ========== Controller Log ==========
    
    def log_controller_event(self, machine_name: str, event_type: str, 
                            message: str, job_id: str = None, 
                            level: str = "info", metadata: Dict = None):
        """Log controller activity"""
        self.conn.execute("""
            INSERT INTO controller_log 
            (machine_name, job_id, event_type, message, level, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (machine_name, job_id, event_type, message, level, 
              json.dumps(metadata) if metadata else None))
        self.conn.commit()
    
    def get_controller_logs(self, job_id: str = None, limit: int = 100) -> List[Dict]:
        """Get controller logs"""
        if job_id:
            cursor = self.conn.execute("""
                SELECT * FROM controller_log 
                WHERE job_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (job_id, limit))
        else:
            cursor = self.conn.execute("""
                SELECT * FROM controller_log 
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== Ideation Results ==========
    
    def save_ideation_result(self, job_id: str, iteration: int, 
                            prompt: str, enhanced_prompt: str = None,
                            score: float = None, metadata: Dict = None) -> int:
        """Save prompt ideation result"""
        cursor = self.conn.execute("""
            INSERT INTO ideation_results 
            (job_id, iteration, prompt, enhanced_prompt, score, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (job_id, iteration, prompt, enhanced_prompt, score,
              json.dumps(metadata) if metadata else None))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_ideation_results(self, job_id: str) -> List[Dict]:
        """Get all ideation results for job"""
        cursor = self.conn.execute("""
            SELECT * FROM ideation_results 
            WHERE job_id = ? 
            ORDER BY iteration
        """, (job_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def select_ideation_result(self, job_id: str, iteration: int):
        """Mark ideation result as selected"""
        self.conn.execute("""
            UPDATE ideation_results SET selected = 1 
            WHERE job_id = ? AND iteration = ?
        """, (job_id, iteration))
        self.conn.commit()
    
    # ========== Image Metadata ==========
    
    def save_image_metadata(self, job_id: str, image_path: str, stage: str,
                           width: int = None, height: int = None,
                           face_count: int = None, face_coordinates: List = None,
                           **kwargs) -> int:
        """Save image metadata"""
        cursor = self.conn.execute("""
            INSERT INTO image_metadata 
            (job_id, image_path, stage, width, height, face_count, 
             face_coordinates, quality_score, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (job_id, image_path, stage, width, height, face_count,
              json.dumps(face_coordinates) if face_coordinates else None,
              kwargs.get('quality_score'),
              json.dumps(kwargs.get('metadata', {}))))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_image_metadata(self, job_id: str, stage: str = None) -> List[Dict]:
        """Get image metadata"""
        if stage:
            cursor = self.conn.execute("""
                SELECT * FROM image_metadata 
                WHERE job_id = ? AND stage = ?
                ORDER BY created_at
            """, (job_id, stage))
        else:
            cursor = self.conn.execute("""
                SELECT * FROM image_metadata 
                WHERE job_id = ?
                ORDER BY created_at
            """, (job_id,))
        
        results = []
        for row in cursor.fetchall():
            meta = dict(row)
            if meta['face_coordinates']:
                meta['face_coordinates'] = json.loads(meta['face_coordinates'])
            if meta['metadata']:
                meta['metadata'] = json.loads(meta['metadata'])
            results.append(meta)
        return results
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# Singleton instance
_db_instance = None

def get_face_changer_db(db_path: str = None) -> FaceChangerDatabase:
    """Get or create database singleton"""
    global _db_instance
    if _db_instance is None:
        _db_instance = FaceChangerDatabase(db_path or "data/face_changer.db")
    return _db_instance
```

### Task 2.3: Create Database __init__.py
**Estimated:** 15 minutes

```python
# face_changer/database/__init__.py
"""
Face-Changer Database Layer

Domain-specific database separate from engine database.
Handles pipeline results, metadata, and domain-specific state.
"""

from .models import FaceChangerDatabase, get_face_changer_db

__all__ = ['FaceChangerDatabase', 'get_face_changer_db']
```

---

## Phase 3: Custom Actions

### Task 3.1: AI Actions - Enhance Prompt
**Estimated:** 2 hours

```python
# face_changer/actions/ai/enhance_prompt_action.py
"""
Enhance Prompt Action

Uses Claude to enhance user prompts for better image generation.
Stores result in face_changer database (not engine database).
"""
import logging
from typing import Dict, Any
from statemachine_engine.actions import BaseAction
from anthropic import Anthropic
from face_changer.database import get_face_changer_db

logger = logging.getLogger(__name__)

class EnhancePromptAction(BaseAction):
    """
    Enhance prompt using Claude AI.
    
    YAML Usage:
        actions:
          - type: enhance_prompt
            params:
              api_key: "${ANTHROPIC_API_KEY}"
              model: "claude-3-5-sonnet-20241022"
              max_tokens: 1024
              success: prompt_enhanced
    """
    
    async def execute(self, context: Dict[str, Any]) -> str:
        job_id = context.get('job_id', 'unknown')
        job_data = context.get('data', {})
        
        # Get prompt from job data
        original_prompt = job_data.get('pony_prompt') or job_data.get('flux_prompt')
        if not original_prompt:
            logger.error(f"[{job_id}] No prompt found in job data")
            return 'error'
        
        # Get config
        api_key = self.config.get('api_key')
        model = self.config.get('model', 'claude-3-5-sonnet-20241022')
        max_tokens = self.config.get('max_tokens', 1024)
        
        if not api_key:
            logger.error(f"[{job_id}] ANTHROPIC_API_KEY not configured")
            return 'error'
        
        try:
            # Call Claude
            client = Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{
                    "role": "user",
                    "content": f"""Enhance this image generation prompt for better results.
Keep it concise but descriptive. Focus on visual details.

Original prompt: {original_prompt}

Enhanced prompt:"""
                }]
            )
            
            enhanced_prompt = response.content[0].text.strip()
            
            # Store in face_changer database
            db = get_face_changer_db()
            db.update_pipeline_result(
                job_id=job_id,
                stage='prompt_enhancement',
                status='completed',
                output_data={
                    'original_prompt': original_prompt,
                    'enhanced_prompt': enhanced_prompt,
                    'model': model,
                    'tokens_used': response.usage.total_tokens
                }
            )
            
            # Update context for next action
            context['enhanced_prompt'] = enhanced_prompt
            
            logger.info(f"[{job_id}] Prompt enhanced: {original_prompt[:50]}... → {enhanced_prompt[:50]}...")
            
            return self.config.get('success', 'prompt_enhanced')
            
        except Exception as e:
            logger.error(f"[{job_id}] Prompt enhancement failed: {e}")
            
            db = get_face_changer_db()
            db.update_pipeline_result(
                job_id=job_id,
                stage='prompt_enhancement',
                status='failed',
                error_message=str(e)
            )
            
            return 'error'
```

### Task 3.2: Pipeline Actions - Initialize Pipeline
**Estimated:** 1 hour

```python
# face_changer/actions/pipeline/initialize_pipeline_action.py
"""
Initialize Pipeline Action

Creates pipeline state in face_changer database when new job starts.
"""
import logging
from typing import Dict, Any
from statemachine_engine.actions import BaseAction
from face_changer.database import get_face_changer_db

logger = logging.getLogger(__name__)

class InitializePipelineAction(BaseAction):
    """
    Initialize pipeline state for new job.
    
    YAML Usage:
        actions:
          - type: initialize_pipeline
            params:
              stages: ['sdxl_generation', 'face_processing', 'description']
              success: pipeline_initialized
    """
    
    async def execute(self, context: Dict[str, Any]) -> str:
        job_id = context.get('job_id', 'unknown')
        job_type = context.get('job_type', 'unknown')
        
        try:
            db = get_face_changer_db()
            
            # Create pipeline state
            db.create_pipeline_state(
                job_id=job_id,
                current_stage='initialization'
            )
            
            # Create pipeline result entries for each stage
            stages = self.config.get('stages', [
                'sdxl_generation',
                'face_processing',
                'description'
            ])
            
            for stage in stages:
                db.create_pipeline_result(
                    job_id=job_id,
                    stage=stage,
                    status='pending'
                )
            
            # Log initialization
            db.log_controller_event(
                machine_name=context.get('machine_name', 'controller'),
                job_id=job_id,
                event_type='pipeline_initialized',
                message=f"Pipeline initialized for {job_type} job",
                metadata={'stages': stages}
            )
            
            logger.info(f"[{job_id}] Pipeline initialized with {len(stages)} stages")
            
            return self.config.get('success', 'pipeline_initialized')
            
        except Exception as e:
            logger.error(f"[{job_id}] Pipeline initialization failed: {e}")
            return 'error'
```

### Task 3.3: Job Management Actions - Create Sub-Job
**Estimated:** 1.5 hours

```python
# face_changer/actions/job_management/create_job_action.py
"""
Create Job Action

Creates sub-jobs in engine database for pipeline stages.
Updates face_changer database with job references.
"""
import logging
from typing import Dict, Any
from statemachine_engine.actions import BaseAction
from statemachine_engine.database import get_job_model
from face_changer.database import get_face_changer_db

logger = logging.getLogger(__name__)

class CreateJobAction(BaseAction):
    """
    Create sub-job in engine database.
    
    YAML Usage:
        actions:
          - type: create_job
            params:
              job_type: "sdxl_generation"
              source_job_id: "{job_id}"
              data_fields: ["pony_prompt", "enhanced_prompt"]
              success: job_created
    """
    
    async def execute(self, context: Dict[str, Any]) -> str:
        source_job_id = context.get('job_id', 'unknown')
        
        try:
            # Get configuration
            job_type = self.config.get('job_type')
            data_fields = self.config.get('data_fields', [])
            
            if not job_type:
                logger.error(f"[{source_job_id}] job_type not specified in config")
                return 'error'
            
            # Build job data from context
            job_data = {}
            source_data = context.get('data', {})
            for field in data_fields:
                if field in context:
                    job_data[field] = context[field]
                elif field in source_data:
                    job_data[field] = source_data[field]
            
            # Create job in engine database
            job_model = get_job_model()
            sub_job_id = job_model.create_job(
                job_type=job_type,
                data=job_data,
                source_job_id=source_job_id
            )
            
            # Update face_changer database with reference
            fc_db = get_face_changer_db()
            update_data = {f"{job_type}_job_id": sub_job_id}
            fc_db.update_pipeline_state(source_job_id, **update_data)
            
            # Log creation
            fc_db.log_controller_event(
                machine_name=context.get('machine_name', 'controller'),
                job_id=source_job_id,
                event_type='sub_job_created',
                message=f"Created {job_type} job: {sub_job_id}",
                metadata={'sub_job_id': sub_job_id, 'job_type': job_type}
            )
            
            # Store in context for reference
            context[f'{job_type}_job_id'] = sub_job_id
            
            logger.info(f"[{source_job_id}] Created sub-job {sub_job_id} ({job_type})")
            
            return self.config.get('success', 'job_created')
            
        except Exception as e:
            logger.error(f"[{source_job_id}] Job creation failed: {e}")
            return 'error'
```

---

## Phase 4: State Machine Configurations

### Task 4.1: Controller Configuration
**Estimated:** 3 hours

```yaml
# config/controller.yaml
name: "Pipeline Controller"
description: "Orchestrates multi-stage image generation pipeline"

initial_state: monitoring

metadata:
  machine_name: controller
  version: "2.0.0"

states:
  # Monitoring loop
  - monitoring
  
  # Pipeline initialization
  - initializing_pipeline
  - creating_sdxl_job
  
  # Stage completion handling
  - handling_sdxl_completion
  - creating_face_job
  - handling_face_completion
  - creating_descriptor_job
  - handling_descriptor_completion
  
  # Finalization
  - finalizing_pipeline
  - completed

events:
  # System events
  - initialized
  - new_pony_flux_job
  - no_events
  
  # Pipeline events
  - pipeline_initialized
  - sdxl_job_created
  - face_job_created
  - descriptor_job_created
  - pipeline_finalized
  
  # Completion events (from workers)
  - sdxl_job_done_relay
  - face_job_completed
  - descriptor_job_done

transitions:
  # === Monitoring ===
  - from: monitoring
    to: monitoring
    event: no_events
  
  - from: monitoring
    to: initializing_pipeline
    event: new_pony_flux_job
  
  # === Pipeline Initialization ===
  - from: initializing_pipeline
    to: creating_sdxl_job
    event: pipeline_initialized
  
  - from: creating_sdxl_job
    to: monitoring
    event: sdxl_job_created
  
  # === SDXL Completion ===
  - from: monitoring
    to: handling_sdxl_completion
    event: sdxl_job_done_relay
  
  - from: handling_sdxl_completion
    to: creating_face_job
    event: face_job_created
  
  # === Face Processing Completion ===
  - from: monitoring
    to: handling_face_completion
    event: face_job_completed
  
  - from: handling_face_completion
    to: creating_descriptor_job
    event: descriptor_job_created
  
  # === Descriptor Completion ===
  - from: monitoring
    to: handling_descriptor_completion
    event: descriptor_job_done
  
  - from: handling_descriptor_completion
    to: finalizing_pipeline
    event: pipeline_finalized
  
  - from: finalizing_pipeline
    to: monitoring
    event: initialized

actions:
  # === Monitoring ===
  monitoring:
    - type: log
      message: "Controller monitoring for events..."
    - type: check_database_queue
      description: "Check for new pony_flux jobs"
      job_type: pony_flux
      machine_type: controller
    - type: check_events
      description: "Check for completion events"
      event_types: 
        - "sdxl_job_done_relay"
        - "face_job_completed"
        - "descriptor_job_done"
  
  # === Pipeline Initialization ===
  initializing_pipeline:
    - type: log
      message: "Initializing pipeline for job {job_id}"
      level: info
    - type: initialize_pipeline
      stages:
        - sdxl_generation
        - face_processing
        - description
      success: pipeline_initialized
  
  creating_sdxl_job:
    - type: log
      message: "Creating SDXL generation job..."
    - type: create_job
      job_type: sdxl_generation
      source_job_id: "{job_id}"
      data_fields:
        - pony_prompt
        - flux_prompt
      success: sdxl_job_created
  
  # === SDXL Completion Handling ===
  handling_sdxl_completion:
    - type: log
      message: "SDXL job completed, creating face processing job"
    - type: create_job
      job_type: face_processing
      source_job_id: "{job_id}"
      data_fields:
        - generated_image_path
      success: face_job_created
  
  # === Face Completion Handling ===
  handling_face_completion:
    - type: log
      message: "Face processing completed, creating descriptor job"
    - type: create_job
      job_type: description
      source_job_id: "{job_id}"
      data_fields:
        - final_image_path
      success: descriptor_job_created
  
  # === Descriptor Completion Handling ===
  handling_descriptor_completion:
    - type: log
      message: "All stages completed, finalizing pipeline"
    - type: finalize_pipeline
      success: pipeline_finalized
  
  # === Finalization ===
  finalizing_pipeline:
    - type: log
      message: "Pipeline completed for job {job_id}"
      level: info
    - type: bash
      command: "echo 'Pipeline complete'"
      success: initialized
```

### Task 4.2: SDXL Generator Configuration
**Estimated:** 2 hours

```yaml
# config/sdxl_generator.yaml
name: "SDXL Image Generator"
description: "Generates images using SDXL/Flux models"

initial_state: initializing

metadata:
  machine_name: sdxl_generator
  version: "2.0.0"
  job_type: sdxl_generation

states:
  - initializing
  - waiting
  - enhancing_prompt
  - generating_image
  - verifying_output
  - notifying_controller
  - completed

events:
  - initialized
  - new_job
  - no_jobs
  - prompt_enhanced
  - image_generated
  - output_verified
  - notification_sent
  - error

transitions:
  # Initialization
  - from: initializing
    to: waiting
    event: initialized
  
  # Job checking
  - from: waiting
    to: waiting
    event: no_jobs
  
  - from: waiting
    to: enhancing_prompt
    event: new_job
  
  # Processing
  - from: enhancing_prompt
    to: generating_image
    event: prompt_enhanced
  
  - from: generating_image
    to: verifying_output
    event: image_generated
  
  - from: verifying_output
    to: notifying_controller
    event: output_verified
  
  # Completion
  - from: notifying_controller
    to: completed
    event: notification_sent
  
  - from: completed
    to: waiting
    event: initialized

actions:
  initializing:
    - type: log
      message: "SDXL Generator initializing..."
    - type: bash
      command: "mkdir -p data/images/0-generated"
      success: initialized
  
  waiting:
    - type: log
      message: "Waiting for generation jobs..."
    - type: check_database_queue
      job_type: sdxl_generation
      machine_type: sdxl_generator
  
  enhancing_prompt:
    - type: log
      message: "Enhancing prompt for job {job_id}"
    - type: enhance_prompt
      api_key: "${ANTHROPIC_API_KEY}"
      success: prompt_enhanced
  
  generating_image:
    - type: log
      message: "Generating image: {enhanced_prompt}"
    - type: bash
      command: "./scripts/generate_sdxl.sh {job_id} '{enhanced_prompt}'"
      timeout: 300
      success: image_generated
  
  verifying_output:
    - type: log
      message: "Verifying generated image"
    - type: bash
      command: "./scripts/verify_image.sh {job_id}"
      success: output_verified
  
  notifying_controller:
    - type: log
      message: "Notifying controller of completion"
    - type: send_event
      target: controller
      event_type: sdxl_job_done_relay
      payload:
        job_id: "{job_id}"
        image_path: "data/images/0-generated/{job_id}.png"
      success: notification_sent
  
  completed:
    - type: log
      message: "Job {job_id} completed"
    - type: bash
      command: "echo 'SDXL generation complete'"
      success: initialized
```

### Task 4.3: Face Processor Configuration
**Estimated:** 2 hours

```yaml
# config/face_processor.yaml
name: "Face Processor"
description: "Processes faces in generated images"

initial_state: initializing

metadata:
  machine_name: face_processor
  version: "2.0.0"
  job_type: face_processing

states:
  - initializing
  - waiting
  - extracting_faces
  - verifying_portraits
  - creating_masks
  - merging_images
  - resizing_output
  - notifying_controller
  - completed

events:
  - initialized
  - new_job
  - no_jobs
  - faces_extracted
  - portraits_verified
  - masks_created
  - images_merged
  - output_resized
  - notification_sent

transitions:
  - from: initializing
    to: waiting
    event: initialized
  
  - from: waiting
    to: waiting
    event: no_jobs
  
  - from: waiting
    to: extracting_faces
    event: new_job
  
  - from: extracting_faces
    to: verifying_portraits
    event: faces_extracted
  
  - from: verifying_portraits
    to: creating_masks
    event: portraits_verified
  
  - from: creating_masks
    to: merging_images
    event: masks_created
  
  - from: merging_images
    to: resizing_output
    event: images_merged
  
  - from: resizing_output
    to: notifying_controller
    event: output_resized
  
  - from: notifying_controller
    to: completed
    event: notification_sent
  
  - from: completed
    to: waiting
    event: initialized

actions:
  initializing:
    - type: log
      message: "Face Processor initializing..."
    - type: bash
      command: "mkdir -p data/images/{1-portraits,2-verified,3-masks,4-results,5-resized,6-final}"
      success: initialized
  
  waiting:
    - type: log
      message: "Waiting for face processing jobs..."
    - type: check_database_queue
      job_type: face_processing
      machine_type: face_processor
  
  extracting_faces:
    - type: log
      message: "Extracting faces from {generated_image_path}"
    - type: bash
      command: "./scripts/image/crop_face.sh {job_id}"
      timeout: 60
      success: faces_extracted
  
  verifying_portraits:
    - type: log
      message: "Verifying portrait dimensions"
    - type: bash
      command: "./scripts/image/verify_portrait.sh {job_id}"
      timeout: 30
      success: portraits_verified
  
  creating_masks:
    - type: log
      message: "Creating face masks"
    - type: bash
      command: "./scripts/image/create_mask.sh {job_id}"
      timeout: 60
      success: masks_created
  
  merging_images:
    - type: log
      message: "Merging masked images"
    - type: bash
      command: "./scripts/image/merge_images.sh {job_id}"
      timeout: 60
      success: images_merged
  
  resizing_output:
    - type: log
      message: "Resizing final output"
    - type: bash
      command: "./scripts/image/resize_output.sh {job_id}"
      timeout: 30
      success: output_resized
  
  notifying_controller:
    - type: log
      message: "Notifying controller of completion"
    - type: send_event
      target: controller
      event_type: face_job_completed
      payload:
        job_id: "{job_id}"
        final_image_path: "data/images/6-final/{job_id}.png"
      success: notification_sent
  
  completed:
    - type: log
      message: "Job {job_id} face processing completed"
    - type: bash
      command: "echo 'Face processing complete'"
      success: initialized
```

### Task 4.4: Descriptor Configuration
**Estimated:** 1.5 hours

```yaml
# config/descriptor.yaml
name: "Image Descriptor"
description: "Generates descriptions for processed images"

initial_state: initializing

metadata:
  machine_name: descriptor
  version: "2.0.0"
  job_type: description

states:
  - initializing
  - waiting
  - generating_description
  - saving_description
  - notifying_controller
  - completed

events:
  - initialized
  - new_job
  - no_jobs
  - description_generated
  - description_saved
  - notification_sent

transitions:
  - from: initializing
    to: waiting
    event: initialized
  
  - from: waiting
    to: waiting
    event: no_jobs
  
  - from: waiting
    to: generating_description
    event: new_job
  
  - from: generating_description
    to: saving_description
    event: description_generated
  
  - from: saving_description
    to: notifying_controller
    event: description_saved
  
  - from: notifying_controller
    to: completed
    event: notification_sent
  
  - from: completed
    to: waiting
    event: initialized

actions:
  initializing:
    - type: log
      message: "Descriptor initializing..."
    - type: bash
      command: "mkdir -p data/descriptions"
      success: initialized
  
  waiting:
    - type: log
      message: "Waiting for description jobs..."
    - type: check_database_queue
      job_type: description
      machine_type: descriptor
  
  generating_description:
    - type: log
      message: "Generating description for {final_image_path}"
    - type: generate_description
      api_key: "${ANTHROPIC_API_KEY}"
      success: description_generated
  
  saving_description:
    - type: log
      message: "Saving description"
    - type: bash
      command: "echo '{description}' > data/descriptions/{job_id}.txt"
      success: description_saved
  
  notifying_controller:
    - type: log
      message: "Notifying controller of completion"
    - type: send_event
      target: controller
      event_type: descriptor_job_done
      payload:
        job_id: "{job_id}"
        description_path: "data/descriptions/{job_id}.txt"
      success: notification_sent
  
  completed:
    - type: log
      message: "Job {job_id} description generated"
    - type: bash
      command: "echo 'Description complete'"
      success: initialized
```

---

## Phase 5: Shell Scripts

### Task 5.1: System Management Scripts
**Estimated:** 2 hours

```bash
# scripts/start-system.sh
#!/bin/bash
set -e

echo "🚀 Starting Face-Changer System..."

# Load environment
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Create directories
mkdir -p data/images/{0-generated,1-portraits,2-verified,3-masks,4-results,5-resized,6-final}
mkdir -p data/descriptions logs

# Initialize databases
echo "📊 Initializing databases..."
python -c "
from statemachine_engine.database import get_database
from face_changer.database import get_face_changer_db

# Initialize both databases
engine_db = get_database('${ENGINE_DB_PATH:-data/engine.db}')
fc_db = get_face_changer_db('${FACE_CHANGER_DB_PATH:-data/face_changer.db}')
print('✓ Databases initialized')
"

# Generate FSM diagrams
echo "📚 Generating FSM diagrams..."
statemachine-fsm config/controller.yaml
statemachine-fsm config/sdxl_generator.yaml
statemachine-fsm config/face_processor.yaml
statemachine-fsm config/descriptor.yaml

# Start WebSocket server
echo "🌐 Starting WebSocket server..."
nohup python -m statemachine_engine.monitoring.websocket_server > logs/websocket.log 2>&1 &
sleep 2

# Start UI server
echo "🖥️  Starting Web UI..."
nohup statemachine-ui > logs/ui.log 2>&1 &
sleep 2

# Start state machines
echo "🤖 Starting state machines..."

nohup statemachine config/controller.yaml > logs/controller.log 2>&1 &
sleep 1

nohup statemachine config/sdxl_generator.yaml > logs/sdxl_generator.log 2>&1 &
sleep 1

nohup statemachine config/face_processor.yaml > logs/face_processor.log 2>&1 &
sleep 1

nohup statemachine config/descriptor.yaml > logs/descriptor.log 2>&1 &
sleep 1

echo "✅ System started successfully!"
echo ""
echo "================================"
echo "📊 WebSocket server: http://localhost:3002/health"
echo "🌐 Web UI: http://localhost:3001"
echo "📋 View logs: tail -f logs/*.log"
echo ""
echo "🛑 Stop: ./scripts/stop-system.sh"
echo "================================"
```

```bash
# scripts/stop-system.sh
#!/bin/bash

echo "🛑 Stopping Face-Changer System..."

# Kill all state machines
pkill -f "statemachine config/"
pkill -f "statemachine_engine.monitoring.websocket_server"
pkill -f "statemachine-ui"

echo "✅ System stopped"
```

```bash
# scripts/add-job.sh
#!/bin/bash

# Add job to queue
JOB_TYPE="${1:-pony_flux}"
PONY_PROMPT="${2:-a beautiful portrait}"
FLUX_PROMPT="${3:-$PONY_PROMPT}"

python -m statemachine_engine.database.cli add-job \
    --type "$JOB_TYPE" \
    --data "{
        \"pony_prompt\": \"$PONY_PROMPT\",
        \"flux_prompt\": \"$FLUX_PROMPT\"
    }"

echo "✅ Job added"
echo "📊 Monitor: http://localhost:3001"
```

### Task 5.2: Image Processing Scripts
**Estimated:** 4 hours

```bash
# scripts/image/crop_face.sh
#!/bin/bash
# Extract face from generated image

JOB_ID="$1"
INPUT_DIR="data/images/0-generated"
OUTPUT_DIR="data/images/1-portraits"

# Face detection and cropping logic
# TODO: Port from original face-changer
```

```bash
# scripts/image/verify_portrait.sh
#!/bin/bash
# Verify portrait meets size requirements

JOB_ID="$1"
INPUT_DIR="data/images/1-portraits"
OUTPUT_DIR="data/images/2-verified"

# Verification logic
# TODO: Port from original face-changer
```

```bash
# scripts/image/create_mask.sh
#!/bin/bash
# Create face mask for inpainting

JOB_ID="$1"
INPUT_DIR="data/images/2-verified"
OUTPUT_DIR="data/images/3-masks"

# Mask creation logic
# TODO: Port from original face-changer
```

---

## Phase 6: Testing

### Task 6.1: Unit Tests for Actions
**Estimated:** 4 hours

```python
# tests/test_actions/test_enhance_prompt_action.py
import pytest
from unittest.mock import Mock, patch
from face_changer.actions.ai.enhance_prompt_action import EnhancePromptAction

@pytest.mark.asyncio
async def test_enhance_prompt_success(mocker):
    """Test successful prompt enhancement"""
    # Mock Anthropic API
    mock_response = Mock()
    mock_response.content = [Mock(text="Enhanced prompt here")]
    mock_response.usage.total_tokens = 100
    
    mock_client = Mock()
    mock_client.messages.create.return_value = mock_response
    
    mocker.patch('face_changer.actions.ai.enhance_prompt_action.Anthropic',
                 return_value=mock_client)
    
    # Mock database
    mock_db = Mock()
    mocker.patch('face_changer.actions.ai.enhance_prompt_action.get_face_changer_db',
                 return_value=mock_db)
    
    # Execute action
    action = EnhancePromptAction({
        'api_key': 'test-key',
        'success': 'prompt_enhanced'
    })
    
    context = {
        'job_id': 'test_001',
        'data': {'pony_prompt': 'original prompt'}
    }
    
    result = await action.execute(context)
    
    assert result == 'prompt_enhanced'
    assert context['enhanced_prompt'] == 'Enhanced prompt here'
    mock_db.update_pipeline_result.assert_called_once()
```

### Task 6.2: Integration Tests
**Estimated:** 3 hours

```python
# tests/test_integration/test_pipeline_flow.py
import pytest
import asyncio
from statemachine_engine.database import get_job_model
from face_changer.database import get_face_changer_db

@pytest.mark.asyncio
async def test_full_pipeline_flow(temp_db):
    """Test complete pipeline from job creation to completion"""
    # This would be a complex test simulating the full flow
    # TODO: Implement based on actual workflow
    pass
```

---

## Phase 7: Documentation & Deployment

### Task 7.1: Create Comprehensive README
**Estimated:** 2 hours

```markdown
# Face-Changer v2.0

AI-powered face image generation and processing pipeline built on [statemachine-engine](https://github.com/sheikkinen/statemachine-engine).

## Features
- Multi-stage image generation (SDXL/Flux)
- Automated face extraction and processing
- AI-powered prompt enhancement
- Image description generation
- Real-time monitoring UI

## Architecture
[Diagram and explanation]

## Installation
[Steps]

## Usage
[Examples]

## Configuration
[Details on YAML configs]

## Development
[Setup for contributors]
```

### Task 7.2: API Documentation
**Estimated:** 1 hour

Document all custom actions, database schema, and integration points.

---

## Timeline & Effort Estimates

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| **Phase 1: Setup** | Project structure, requirements, config | 2-3 hours |
| **Phase 2: Database** | Schema, models, __init__ | 4-5 hours |
| **Phase 3: Actions** | AI, pipeline, job management actions | 6-8 hours |
| **Phase 4: Configs** | 4 state machine YAMLs | 8-10 hours |
| **Phase 5: Scripts** | System mgmt + image processing | 6-8 hours |
| **Phase 6: Testing** | Unit + integration tests | 7-10 hours |
| **Phase 7: Docs** | README, API docs, guides | 3-4 hours |
| **TOTAL** | All phases | **36-48 hours** |

**Recommended Approach:** 5-7 days of focused development (8 hours/day)

---

## Success Criteria

- [  ] ✅ Clean separation: Engine DB vs Face-Changer DB
- [  ] ✅ All 4 state machines running independently
- [  ] ✅ Jobs flow through all 3 stages (SDXL → Face → Descriptor)
- [  ] ✅ Events properly delivered between machines
- [  ] ✅ Real-time monitoring UI showing all machines
- [  ] ✅ Image processing pipeline produces final output
- [  ] ✅ All custom actions working (AI, pipeline, job mgmt)
- [  ] ✅ 80%+ test coverage
- [  ] ✅ Complete documentation

---

## Next Steps

1. **Review this plan** - Ensure approach aligns with goals
2. **Set up dev environment** - Clone statemachine-engine, install dependencies
3. **Start Phase 1** - Create project structure
4. **Work incrementally** - Complete one phase before moving to next
5. **Test continuously** - Validate each component as built
6. **Document as you go** - Keep README updated

**Let's build Face-Changer v2.0!** 🚀
