"""
Tests for RealtimeEventModel exception handling
"""
import pytest
import json
import sqlite3
from pathlib import Path
from statemachine_engine.database.models.base import Database
from statemachine_engine.database.models import get_realtime_event_model


@pytest.fixture
def test_db(tmp_path):
    """Create a test database"""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    return db


@pytest.fixture
def realtime_model(test_db):
    """Create RealtimeEventModel with test database"""
    from statemachine_engine.database.models.realtime_event import RealtimeEventModel
    return RealtimeEventModel(test_db)


def test_log_event_success(realtime_model):
    """Test successful event logging"""
    event_id = realtime_model.log_event(
        'test_machine',
        'state_change',
        {'from_state': 'idle', 'to_state': 'running'}
    )
    assert event_id is not None
    assert event_id > 0


def test_log_event_with_complex_payload(realtime_model):
    """Test logging event with complex nested payload"""
    complex_payload = {
        'from_state': 'idle',
        'to_state': 'running',
        'metadata': {
            'nested': True,
            'values': [1, 2, 3]
        }
    }
    event_id = realtime_model.log_event('test_machine', 'state_change', complex_payload)
    assert event_id is not None


def test_log_event_returns_none_on_db_error(realtime_model):
    """Test that log_event returns None on database error"""
    # Close the database connection to simulate error
    realtime_model.db.db_path = Path("/invalid/path/that/does/not/exist.db")
    
    event_id = realtime_model.log_event('test_machine', 'error', {'msg': 'test'})
    assert event_id is None


def test_get_unconsumed_events_success(realtime_model):
    """Test getting unconsumed events"""
    # Log some events
    realtime_model.log_event('machine1', 'state_change', {'state': 'running'})
    realtime_model.log_event('machine2', 'error', {'error': 'failed'})
    
    events = realtime_model.get_unconsumed_events()
    assert len(events) == 2
    assert events[0]['event_type'] == 'state_change'
    assert events[1]['event_type'] == 'error'


def test_get_unconsumed_events_with_limit(realtime_model):
    """Test limit parameter"""
    # Log 5 events
    for i in range(5):
        realtime_model.log_event(f'machine{i}', 'test', {'index': i})
    
    events = realtime_model.get_unconsumed_events(limit=3)
    assert len(events) == 3


def test_get_unconsumed_events_since_id(realtime_model):
    """Test since_id parameter"""
    # Log events
    id1 = realtime_model.log_event('machine1', 'test', {'num': 1})
    id2 = realtime_model.log_event('machine2', 'test', {'num': 2})
    id3 = realtime_model.log_event('machine3', 'test', {'num': 3})
    
    # Get events since id1
    events = realtime_model.get_unconsumed_events(since_id=id1)
    assert len(events) == 2
    assert events[0]['payload']['num'] == 2
    assert events[1]['payload']['num'] == 3


def test_get_unconsumed_events_handles_invalid_json(realtime_model, test_db):
    """Test that invalid JSON in payload is gracefully handled"""
    # Insert event with invalid JSON directly
    with test_db._get_connection() as conn:
        conn.execute("""
            INSERT INTO realtime_events (machine_name, event_type, payload)
            VALUES (?, ?, ?)
        """, ('test_machine', 'test', 'INVALID_JSON{'))
        conn.commit()
    
    # Log a valid event
    realtime_model.log_event('machine2', 'test', {'valid': True})
    
    # Should return only the valid event
    events = realtime_model.get_unconsumed_events()
    assert len(events) == 1
    assert events[0]['payload']['valid'] is True


def test_get_unconsumed_events_returns_empty_on_db_error(realtime_model):
    """Test that get_unconsumed_events returns empty list on database error"""
    realtime_model.db.db_path = Path("/invalid/path.db")
    
    events = realtime_model.get_unconsumed_events()
    assert events == []


def test_mark_events_consumed_success(realtime_model):
    """Test marking events as consumed"""
    id1 = realtime_model.log_event('machine1', 'test', {'n': 1})
    id2 = realtime_model.log_event('machine2', 'test', {'n': 2})
    
    result = realtime_model.mark_events_consumed([id1, id2])
    assert result is True
    
    # Verify events are consumed
    unconsumed = realtime_model.get_unconsumed_events()
    assert len(unconsumed) == 0


def test_mark_events_consumed_empty_list(realtime_model):
    """Test marking empty list returns True"""
    result = realtime_model.mark_events_consumed([])
    assert result is True


def test_mark_events_consumed_returns_false_on_error(realtime_model):
    """Test that mark_events_consumed returns False on database error"""
    id1 = realtime_model.log_event('machine1', 'test', {'n': 1})
    
    # Break the database connection
    realtime_model.db.db_path = Path("/invalid/path.db")
    
    result = realtime_model.mark_events_consumed([id1])
    assert result is False


def test_cleanup_old_events_success(realtime_model, test_db):
    """Test cleanup of old consumed events"""
    # Log and consume events
    id1 = realtime_model.log_event('machine1', 'test', {'n': 1})
    realtime_model.mark_events_consumed([id1])
    
    # Update consumed_at to be 25 hours ago
    with test_db._get_connection() as conn:
        conn.execute("""
            UPDATE realtime_events
            SET consumed_at = datetime('now', '-25 hours')
            WHERE id = ?
        """, (id1,))
        conn.commit()
    
    # Cleanup events older than 24 hours
    deleted_count = realtime_model.cleanup_old_events(hours_old=24)
    assert deleted_count == 1


def test_cleanup_old_events_does_not_delete_recent(realtime_model):
    """Test that cleanup doesn't delete recent events"""
    id1 = realtime_model.log_event('machine1', 'test', {'n': 1})
    realtime_model.mark_events_consumed([id1])
    
    # Try to cleanup (event is recent)
    deleted_count = realtime_model.cleanup_old_events(hours_old=24)
    assert deleted_count == 0


def test_cleanup_old_events_does_not_delete_unconsumed(realtime_model, test_db):
    """Test that cleanup only deletes consumed events"""
    # Log event but don't consume
    id1 = realtime_model.log_event('machine1', 'test', {'n': 1})
    
    # Make it old
    with test_db._get_connection() as conn:
        conn.execute("""
            UPDATE realtime_events
            SET created_at = strftime('%s', datetime('now', '-25 hours'))
            WHERE id = ?
        """, (id1,))
        conn.commit()
    
    # Try cleanup
    deleted_count = realtime_model.cleanup_old_events(hours_old=24)
    assert deleted_count == 0  # Should not delete unconsumed


def test_cleanup_old_events_returns_negative_on_error(realtime_model):
    """Test that cleanup returns -1 on database error"""
    realtime_model.db.db_path = Path("/invalid/path.db")
    
    deleted_count = realtime_model.cleanup_old_events(hours_old=24)
    assert deleted_count == -1


def test_error_event_logging(realtime_model):
    """Test logging error events with proper payload structure"""
    error_id = realtime_model.log_event(
        'test_machine',
        'error',
        {
            'error_message': 'Test error occurred',
            'job_id': 'job_123',
            'timestamp': 1234567890.0
        }
    )
    assert error_id is not None
    
    # Retrieve and verify
    events = realtime_model.get_unconsumed_events()
    assert len(events) == 1
    assert events[0]['event_type'] == 'error'
    assert events[0]['payload']['error_message'] == 'Test error occurred'
    assert events[0]['payload']['job_id'] == 'job_123'


def test_state_change_event_logging(realtime_model):
    """Test logging state_change events with proper payload structure"""
    event_id = realtime_model.log_event(
        'worker_machine',
        'state_change',
        {
            'from_state': 'idle',
            'to_state': 'processing',
            'event_trigger': 'start_job',
            'timestamp': 1234567890.0
        }
    )
    assert event_id is not None
    
    # Retrieve and verify
    events = realtime_model.get_unconsumed_events()
    assert len(events) == 1
    assert events[0]['event_type'] == 'state_change'
    assert events[0]['payload']['from_state'] == 'idle'
    assert events[0]['payload']['to_state'] == 'processing'
    assert events[0]['payload']['event_trigger'] == 'start_job'
