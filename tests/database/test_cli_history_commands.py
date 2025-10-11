"""
Tests for transition-history and error-history CLI commands
"""
import pytest
import json
import time
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


@pytest.fixture
def setup_transition_data(realtime_model):
    """Setup test data for transition history"""
    # Log several state transitions
    realtime_model.log_event(
        'worker1',
        'state_change',
        {
            'from_state': 'idle',
            'to_state': 'processing',
            'event_trigger': 'start_job',
            'timestamp': time.time()
        }
    )
    realtime_model.log_event(
        'worker1',
        'state_change',
        {
            'from_state': 'processing',
            'to_state': 'completed',
            'event_trigger': 'job_done',
            'timestamp': time.time()
        }
    )
    realtime_model.log_event(
        'worker2',
        'state_change',
        {
            'from_state': 'idle',
            'to_state': 'error',
            'event_trigger': 'error',
            'timestamp': time.time()
        }
    )


@pytest.fixture
def setup_error_data(realtime_model):
    """Setup test data for error history"""
    # Log several errors
    realtime_model.log_event(
        'worker1',
        'error',
        {
            'error_message': 'Connection timeout',
            'job_id': 'job_123',
            'timestamp': time.time()
        }
    )
    realtime_model.log_event(
        'worker2',
        'error',
        {
            'error_message': 'Action not found',
            'job_id': 'job_456',
            'timestamp': time.time()
        }
    )
    realtime_model.log_event(
        'worker1',
        'error',
        {
            'error_message': 'Database error',
            'job_id': None,
            'timestamp': time.time()
        }
    )


def test_transition_history_all_machines(test_db, setup_transition_data):
    """Test querying all transitions"""
    from statemachine_engine.database.models.realtime_event import RealtimeEventModel
    model = RealtimeEventModel(test_db)
    
    with test_db._get_connection() as conn:
        rows = conn.execute("""
            SELECT machine_name, payload
            FROM realtime_events
            WHERE event_type = 'state_change'
            ORDER BY created_at DESC
        """).fetchall()
    
    assert len(rows) == 3
    # Order may vary, just check we have the expected machines
    machine_names = [row['machine_name'] for row in rows]
    assert 'worker1' in machine_names
    assert 'worker2' in machine_names
    
    # Parse a payload and verify structure
    payload = json.loads(rows[0]['payload'])
    assert 'from_state' in payload
    assert 'to_state' in payload
    assert 'event_trigger' in payload


def test_transition_history_filter_by_machine(test_db, setup_transition_data):
    """Test filtering transitions by machine name"""
    with test_db._get_connection() as conn:
        rows = conn.execute("""
            SELECT machine_name, payload
            FROM realtime_events
            WHERE event_type = 'state_change' AND machine_name = ?
            ORDER BY created_at DESC
        """, ('worker1',)).fetchall()
    
    assert len(rows) == 2
    for row in rows:
        assert row['machine_name'] == 'worker1'


def test_transition_history_limit(test_db, setup_transition_data):
    """Test limit parameter"""
    with test_db._get_connection() as conn:
        rows = conn.execute("""
            SELECT id FROM realtime_events
            WHERE event_type = 'state_change'
            ORDER BY created_at DESC
            LIMIT 2
        """).fetchall()
    
    assert len(rows) == 2


def test_error_history_all_machines(test_db, setup_error_data):
    """Test querying all errors"""
    with test_db._get_connection() as conn:
        rows = conn.execute("""
            SELECT machine_name, payload
            FROM realtime_events
            WHERE event_type = 'error'
            ORDER BY created_at DESC
        """).fetchall()
    
    assert len(rows) == 3
    
    # Check first error
    payload = json.loads(rows[0]['payload'])
    assert 'error_message' in payload


def test_error_history_filter_by_machine(test_db, setup_error_data):
    """Test filtering errors by machine name"""
    with test_db._get_connection() as conn:
        rows = conn.execute("""
            SELECT machine_name, payload
            FROM realtime_events
            WHERE event_type = 'error' AND machine_name = ?
            ORDER BY created_at DESC
        """, ('worker1',)).fetchall()
    
    assert len(rows) == 2
    for row in rows:
        assert row['machine_name'] == 'worker1'


def test_error_history_payload_structure(test_db, setup_error_data):
    """Test error payload contains required fields"""
    with test_db._get_connection() as conn:
        rows = conn.execute("""
            SELECT payload FROM realtime_events
            WHERE event_type = 'error'
            LIMIT 1
        """).fetchall()
    
    payload = json.loads(rows[0]['payload'])
    assert 'error_message' in payload
    assert 'timestamp' in payload
    # job_id is optional


def test_transition_history_time_filter(test_db, realtime_model):
    """Test filtering by time range"""
    # Create old transition (simulate by directly modifying timestamp)
    event_id = realtime_model.log_event(
        'old_worker',
        'state_change',
        {'from_state': 'a', 'to_state': 'b', 'event_trigger': 'e', 'timestamp': time.time()}
    )
    
    # Update to be 25 hours old
    with test_db._get_connection() as conn:
        conn.execute("""
            UPDATE realtime_events
            SET created_at = strftime('%s', datetime('now', '-25 hours'))
            WHERE id = ?
        """, (event_id,))
        conn.commit()
    
    # Create recent transition
    realtime_model.log_event(
        'new_worker',
        'state_change',
        {'from_state': 'x', 'to_state': 'y', 'event_trigger': 'e', 'timestamp': time.time()}
    )
    
    # Query last 24 hours
    with test_db._get_connection() as conn:
        rows = conn.execute("""
            SELECT machine_name FROM realtime_events
            WHERE event_type = 'state_change'
            AND created_at > strftime('%s', datetime('now', '-24 hours'))
        """).fetchall()
    
    assert len(rows) == 1
    assert rows[0]['machine_name'] == 'new_worker'


def test_no_transitions_found(test_db):
    """Test behavior when no transitions exist"""
    with test_db._get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM realtime_events
            WHERE event_type = 'state_change'
        """).fetchall()
    
    assert len(rows) == 0


def test_no_errors_found(test_db):
    """Test behavior when no errors exist"""
    with test_db._get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM realtime_events
            WHERE event_type = 'error'
        """).fetchall()
    
    assert len(rows) == 0


def test_mixed_event_types(test_db, realtime_model):
    """Test that queries correctly filter by event_type"""
    # Log different event types
    realtime_model.log_event('m1', 'state_change', {'from_state': 'a', 'to_state': 'b', 'event_trigger': 'e', 'timestamp': time.time()})
    realtime_model.log_event('m1', 'error', {'error_message': 'test', 'timestamp': time.time()})
    realtime_model.log_event('m1', 'job_started', {'job_id': '123', 'timestamp': time.time()})
    realtime_model.log_event('m1', 'state_change', {'from_state': 'b', 'to_state': 'c', 'event_trigger': 'e2', 'timestamp': time.time()})
    
    # Query only state_change
    with test_db._get_connection() as conn:
        state_rows = conn.execute("""
            SELECT * FROM realtime_events WHERE event_type = 'state_change'
        """).fetchall()
        
        error_rows = conn.execute("""
            SELECT * FROM realtime_events WHERE event_type = 'error'
        """).fetchall()
    
    assert len(state_rows) == 2
    assert len(error_rows) == 1


def test_transition_with_invalid_payload_structure(test_db):
    """Test handling of malformed payload in transition query"""
    from statemachine_engine.database.models.realtime_event import RealtimeEventModel
    model = RealtimeEventModel(test_db)
    
    # Insert event with incomplete payload
    with test_db._get_connection() as conn:
        conn.execute("""
            INSERT INTO realtime_events (machine_name, event_type, payload)
            VALUES (?, ?, ?)
        """, ('bad_machine', 'state_change', json.dumps({'incomplete': 'data'})))
        conn.commit()
    
    # Should be retrievable, just with missing fields
    events = model.get_unconsumed_events()
    assert len(events) == 1
    assert events[0]['payload'].get('from_state') is None
