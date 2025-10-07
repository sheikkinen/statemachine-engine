"""
Test the walking skeleton implementation
"""

import asyncio
import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / '../src'))

from statemachine_engine.database.models import Database, JobModel
from statemachine_engine.core.engine import StateMachineEngine

@pytest.mark.asyncio
async def test_database_queue():
    """Test basic database queue functionality"""
    import os
    import time
    import tempfile
    
    # Use a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    test_db_file = os.path.join(temp_dir, f"test_pipeline_{int(time.time())}.db")
    
    try:
        db = Database(test_db_file)
        job_model = JobModel(db)
        
        # Initially empty
        pending_jobs = job_model.list_jobs(status='pending')
        assert len(pending_jobs) == 0
        
        # Add a job
        job_id = job_model.create_job("test_job_1", job_type="face_processing", 
                                      data={"input_image_path": "/test/image.jpg", "user_prompt": "test prompt"})
        assert job_id is not None
        
        pending_jobs = job_model.list_jobs(status='pending')
        assert len(pending_jobs) == 1
        
        # Get the job
        retrieved_job = pending_jobs[0]
        assert retrieved_job is not None
        assert retrieved_job["job_id"] == "test_job_1"  # The job_id string, not database ID
        assert retrieved_job["data"]["input_image_path"] == "/test/image.jpg"
        assert retrieved_job["data"]["user_prompt"] == "test prompt"
        
        # Complete the job
        job_model.complete_job("test_job_1")
        
        # No more pending jobs
        pending_jobs = job_model.list_jobs(status='pending')
        assert len(pending_jobs) == 0
        
        # Check job is in completed state
        completed_job = job_model.get_job("test_job_1")
        assert completed_job is not None
        assert completed_job['status'] == 'completed'
    finally:
        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.mark.asyncio
async def test_state_machine_config_loading():
    """Test state machine configuration loading"""
    engine = StateMachineEngine()
    
    # conftest.py ensures we're in project root, so use relative path
    config_path = Path('config/walking_skeleton.yaml')
    if not config_path.exists():
        pytest.skip(f"Config file not found: {config_path}")
    await engine.load_config(str(config_path))
    
    assert engine.config is not None
    assert engine.current_state == 'waiting'
    assert 'states' in engine.config
    assert 'transitions' in engine.config
    assert 'actions' in engine.config

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, '-v'])
