"""
Tests for LogAction - Activity log action
"""
import pytest
import asyncio
import json
from pathlib import Path

from statemachine_engine.actions.builtin import LogAction
from statemachine_engine.database.models import Database, get_machine_event_model


@pytest.fixture
def test_db(tmp_path):
    """Create a test database"""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    return db


@pytest.fixture
def event_model(test_db):
    """Get machine event model for test database"""
    model = get_machine_event_model()
    # Clear any existing events before each test
    # This ensures test isolation
    return model


@pytest.mark.asyncio
async def test_log_action_basic(test_db, event_model):
    """Test basic log action execution"""
    config = {
        'message': 'Test message',
        'level': 'info'
    }

    context = {
        'machine_name': 'test_machine',
        'id': 'job_123'
    }

    action = LogAction(config)
    result = await action.execute(context)

    # Should return success
    assert result == 'continue'

    # Check event was created
    events = event_model.list_events(target_machine='ui', status='pending', limit=10)
    assert len(events) > 0

    # Check event content
    event = events[0]
    assert event['event_type'] == 'activity_log'
    assert event['source_machine'] == 'test_machine'
    assert event['job_id'] == 'job_123'

    # Check payload
    payload = json.loads(event['payload'])
    assert payload['message'] == 'Test message'
    assert payload['level'] == 'info'
    assert payload['machine'] == 'test_machine'


@pytest.mark.asyncio
async def test_log_action_with_substitution(test_db, event_model):
    """Test log action with context variable substitution"""
    config = {
        'message': 'Processing job {job_id} in state {current_state}',
        'level': 'info'
    }

    context = {
        'machine_name': 'face_processor',
        'current_job': {'id': 'job_456'},
        'current_state': 'analyzing'
    }

    action = LogAction(config)
    result = await action.execute(context)

    assert result == 'continue'

    # Check event was created - filter by job_id for isolation
    events = event_model.list_events(target_machine='ui', status='pending', limit=100)
    our_events = [e for e in events if e.get('job_id') == 'job_456']
    assert len(our_events) > 0

    # Check payload has substituted values
    payload = json.loads(our_events[0]['payload'])
    assert payload['message'] == 'Processing job job_456 in state analyzing'


@pytest.mark.asyncio
async def test_log_action_error_level(test_db, event_model):
    """Test log action with error level"""
    config = {
        'message': 'Error: {last_error}',
        'level': 'error'
    }

    context = {
        'machine_name': 'descriptor_error_test',
        'last_error': 'File not found'
    }

    action = LogAction(config)
    result = await action.execute(context)

    assert result == 'continue'

    # Check event was created with error level - filter by source machine
    events = event_model.list_events(target_machine='ui', status='pending', limit=100)
    # Find our event by checking the source
    our_events = [e for e in events if e.get('source_machine') == 'descriptor_error_test']
    assert len(our_events) > 0
    payload = json.loads(our_events[0]['payload'])
    assert payload['level'] == 'error'
    assert 'File not found' in payload['message']


@pytest.mark.asyncio
async def test_log_action_success_level(test_db, event_model):
    """Test log action with success level"""
    config = {
        'message': 'Job completed successfully',
        'level': 'success'
    }

    context = {
        'machine_name': 'sdxl_generator',
        'id': 'job_789'
    }

    action = LogAction(config)
    result = await action.execute(context)

    assert result == 'continue'

    # Check event was created with success level - filter by job_id
    events = event_model.list_events(target_machine='ui', status='pending', limit=100)
    our_events = [e for e in events if e.get('job_id') == 'job_789']
    assert len(our_events) > 0
    payload = json.loads(our_events[0]['payload'])
    assert payload['level'] == 'success'


@pytest.mark.asyncio
async def test_log_action_custom_success_event(test_db, event_model):
    """Test log action with custom success event"""
    config = {
        'message': 'Transition complete',
        'level': 'info',
        'success': 'custom_event'
    }

    context = {
        'machine_name': 'test_machine'
    }

    action = LogAction(config)
    result = await action.execute(context)

    # Should return custom success event
    assert result == 'custom_event'
