"""
Generic fixtures for engine tests.

These fixtures provide common test infrastructure for engine components:
- Temporary databases
- Mock jobs and events
- State machine configurations
"""

import pytest
import os
import tempfile
import sqlite3
from pathlib import Path


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def temp_working_dir():
    """Create a temporary working directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        original_dir = os.getcwd()
        os.chdir(tmpdir)
        yield tmpdir
        os.chdir(original_dir)


@pytest.fixture
def mock_job_data():
    """Provide mock job data in the new data={} structure."""
    return {
        'job_id': 'test_job_123',
        'job_type': 'test_processing',
        'status': 'pending',
        'data': {
            'input_path': '/test/input.jpg',
            'output_path': '/test/output.jpg',
            'params': {'quality': 'high'}
        }
    }


@pytest.fixture
def mock_event_data():
    """Provide mock event data for testing."""
    return {
        'source_machine': 'test_source',
        'target_machine': 'test_target',
        'event_name': 'test_event',
        'payload': {'key': 'value'}
    }
