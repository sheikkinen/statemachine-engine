"""
Test machine-agnostic job queue polling for v2.0 controller architecture.

Tests that check_database_queue can claim jobs regardless of machine_type
when machine_type parameter is None (Option A implementation).
"""
import pytest
import tempfile
import os
from pathlib import Path
from statemachine_engine.database import Database
from statemachine_engine.database.models.job import JobModel


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(str(db_path))
        yield db


@pytest.fixture
def job_model(temp_db):
    """Create JobModel instance"""
    return JobModel(temp_db)


def test_get_next_job_with_machine_type_filter(job_model):
    """Test traditional v1.0 behavior - filter by machine_type"""
    # Create jobs for different machines
    job_model.create_job(
        job_id="job_worker_a",
        job_type="processing",
        machine_type="worker_a"
    )
    job_model.create_job(
        job_id="job_worker_b",
        job_type="processing",
        machine_type="worker_b"
    )
    
    # Worker A should only get its own job
    job = job_model.get_next_job(job_type="processing", machine_type="worker_a")
    assert job is not None
    assert job['job_id'] == "job_worker_a"
    assert job['machine_type'] == "worker_a"
    
    # Worker B should only get its own job
    job = job_model.get_next_job(job_type="processing", machine_type="worker_b")
    assert job is not None
    assert job['job_id'] == "job_worker_b"
    assert job['machine_type'] == "worker_b"


def test_get_next_job_without_machine_type_claims_any(job_model):
    """Test v2.0 controller behavior - claim ANY job when machine_type=None"""
    # Create jobs assigned to different machines
    job_model.create_job(
        job_id="job_sdxl_generator",
        job_type="sdxl_generation",
        machine_type="sdxl_generator",
        priority=5
    )
    job_model.create_job(
        job_id="job_face_processor",
        job_type="face_processing",
        machine_type="face_processor",
        priority=3
    )
    
    # Controller polls for sdxl_generation jobs WITHOUT machine_type filter
    job = job_model.get_next_job(job_type="sdxl_generation", machine_type=None)
    assert job is not None
    assert job['job_id'] == "job_sdxl_generator"
    assert job['machine_type'] == "sdxl_generator"  # Job still has assigned_machine
    assert job['status'] == "processing"  # Should be claimed
    
    # Controller polls for face_processing jobs WITHOUT machine_type filter
    job = job_model.get_next_job(job_type="face_processing", machine_type=None)
    assert job is not None
    assert job['job_id'] == "job_face_processor"
    assert job['machine_type'] == "face_processor"
    assert job['status'] == "processing"


def test_get_next_job_respects_priority_across_machines(job_model):
    """Test that machine-agnostic polling respects priority ordering"""
    # Create jobs with different priorities
    job_model.create_job(
        job_id="low_priority",
        job_type="work",
        machine_type="machine_a",
        priority=10  # Low priority
    )
    job_model.create_job(
        job_id="high_priority",
        job_type="work",
        machine_type="machine_b",
        priority=1  # High priority
    )
    job_model.create_job(
        job_id="medium_priority",
        job_type="work",
        machine_type="machine_c",
        priority=5  # Medium priority
    )
    
    # Controller should get highest priority job first
    job = job_model.get_next_job(job_type="work", machine_type=None)
    assert job is not None
    assert job['job_id'] == "high_priority"
    assert job['priority'] == 1
    
    # Next poll should get medium priority
    job = job_model.get_next_job(job_type="work", machine_type=None)
    assert job is not None
    assert job['job_id'] == "medium_priority"
    assert job['priority'] == 5
    
    # Final poll should get low priority
    job = job_model.get_next_job(job_type="work", machine_type=None)
    assert job is not None
    assert job['job_id'] == "low_priority"
    assert job['priority'] == 10


def test_mixed_polling_v1_and_v2_architectures(job_model):
    """Test that v1.0 workers and v2.0 controllers can coexist"""
    # Create jobs for mixed architecture
    job_model.create_job(
        job_id="job_for_specific_worker",
        job_type="task_a",
        machine_type="worker_1"
    )
    job_model.create_job(
        job_id="job_for_any_worker",
        job_type="task_b",
        machine_type="worker_2"
    )
    
    # V1.0 worker polls with machine_type (specific filtering)
    job = job_model.get_next_job(job_type="task_a", machine_type="worker_1")
    assert job is not None
    assert job['job_id'] == "job_for_specific_worker"
    
    # V2.0 controller polls without machine_type (any job of type)
    job = job_model.get_next_job(job_type="task_b", machine_type=None)
    assert job is not None
    assert job['job_id'] == "job_for_any_worker"


def test_no_jobs_available_returns_none(job_model):
    """Test that None is returned when no jobs match criteria"""
    job_model.create_job(
        job_id="wrong_type",
        job_type="other_work",
        machine_type="some_machine"
    )
    
    # Search for non-existent job_type
    job = job_model.get_next_job(job_type="nonexistent", machine_type=None)
    assert job is None
    
    # Search with machine_type that doesn't match
    job = job_model.get_next_job(job_type="other_work", machine_type="wrong_machine")
    assert job is None


def test_empty_string_machine_type_filters_for_empty_string(job_model):
    """Test that empty string machine_type is treated as a specific value, not None"""
    job_model.create_job(
        job_id="no_machine",
        job_type="work",
        machine_type=""  # Empty string
    )
    job_model.create_job(
        job_id="with_machine",
        job_type="work",
        machine_type="machine_a"
    )
    
    # Search with empty string should only match empty string jobs
    job = job_model.get_next_job(job_type="work", machine_type="")
    assert job is not None
    assert job['job_id'] == "no_machine"
    
    # Search with None should match both
    job = job_model.get_next_job(job_type="work", machine_type=None)
    assert job is not None
    assert job['job_id'] == "with_machine"  # Gets second one (first already claimed)
