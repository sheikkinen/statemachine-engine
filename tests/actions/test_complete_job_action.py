"""Test complete_job action"""
import pytest
import uuid
from statemachine_engine.actions.builtin import CompleteJobAction
from statemachine_engine.database.models import get_job_model

@pytest.mark.asyncio
async def test_complete_job_basic():
    """Test basic job completion"""
    job_model = get_job_model()
    
    # Create a test job with unique ID 
    job_id = f"test_complete_{uuid.uuid4().hex[:8]}"
    job_model.create_job(job_id, "test_type", data={"data": "test"})
    
    # get_next_job marks it as processing automatically
    job = job_model.get_next_job(job_type="test_type")
    assert job is not None
    
    # Complete the job via action
    action = CompleteJobAction({
        'job_id': '{job_id}',
        'success': 'job_completed'
    })
    
    context = {'job_id': job_id, 'machine_name': 'test_machine'}
    result = await action.execute(context)
    
    assert result == 'job_completed'
    
    # Verify job is completed
    job = job_model.get_job(job_id)
    assert job['status'] == 'completed'
    assert job['completed_at'] is not None


@pytest.mark.asyncio
async def test_complete_job_missing_id():
    """Test complete_job with missing job_id"""
    action = CompleteJobAction({
        'job_id': '{job_id}',
        'error': 'completion_failed'
    })
    
    context = {'machine_name': 'test_machine'}  # No job_id
    result = await action.execute(context)
    
    assert result == 'completion_failed'


@pytest.mark.asyncio
async def test_complete_job_literal_id():
    """Test complete_job with literal job_id (no interpolation)"""
    job_model = get_job_model()
    
    # Create a test job with unique ID
    job_id = f"literal_job_{uuid.uuid4().hex[:8]}"
    job_model.create_job(job_id, "test_type", data={"data": "test"})
    job = job_model.get_next_job(job_type="test_type")
    assert job is not None
    
    # Complete with literal ID
    action = CompleteJobAction({
        'job_id': job_id,
        'success': 'done'
    })
    
    context = {'machine_name': 'test_machine'}
    result = await action.execute(context)
    
    assert result == 'done'
    
    job = job_model.get_job(job_id)
    assert job['status'] == 'completed'
