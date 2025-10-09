"""
Tests for JSON payload auto-parsing in engine

Tests the automatic parsing of JSON string payloads to dictionaries
when events are received via Unix socket.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from statemachine_engine.core.engine import StateMachineEngine


@pytest.mark.asyncio
async def test_json_string_payload_auto_parsed():
    """JSON string payloads are automatically parsed to dict"""
    engine = StateMachineEngine('test_machine')
    
    # Mock the config
    engine.config = {
        'initial_state': 'waiting',
        'transitions': [],
        'actions': {}
    }
    engine.current_state = 'waiting'
    
    # Create a socket mock
    mock_socket = MagicMock()
    engine.control_socket = mock_socket
    
    # Simulate receiving event with JSON string payload
    test_event = {
        'type': 'test_event',
        'payload': '{"key": "value", "number": 42, "nested": {"field": "data"}}'
    }
    mock_socket.recvfrom.return_value = (json.dumps(test_event).encode('utf-8'), None)
    
    # Call the method
    await engine._check_control_socket()
    
    # Verify payload was parsed to dict
    stored_event = engine.context.get('event_data')
    assert stored_event is not None
    assert isinstance(stored_event['payload'], dict)
    assert stored_event['payload']['key'] == 'value'
    assert stored_event['payload']['number'] == 42
    assert stored_event['payload']['nested']['field'] == 'data'


@pytest.mark.asyncio
async def test_dict_payload_unchanged():
    """Dict payloads pass through without modification"""
    engine = StateMachineEngine('test_machine')
    
    engine.config = {
        'initial_state': 'waiting',
        'transitions': [],
        'actions': {}
    }
    engine.current_state = 'waiting'
    
    mock_socket = MagicMock()
    engine.control_socket = mock_socket
    
    # Already a dict - should remain unchanged
    test_event = {
        'type': 'test_event',
        'payload': {'key': 'value', 'number': 42}
    }
    mock_socket.recvfrom.return_value = (json.dumps(test_event).encode('utf-8'), None)
    
    await engine._check_control_socket()
    
    stored_event = engine.context.get('event_data')
    assert isinstance(stored_event['payload'], dict)
    assert stored_event['payload'] == {'key': 'value', 'number': 42}


@pytest.mark.asyncio
async def test_invalid_json_fallback_to_empty_dict(caplog):
    """Invalid JSON logs warning and uses empty dict"""
    engine = StateMachineEngine('test_machine')
    
    engine.config = {
        'initial_state': 'waiting',
        'transitions': [],
        'actions': {}
    }
    engine.current_state = 'waiting'
    
    mock_socket = MagicMock()
    engine.control_socket = mock_socket
    
    # Invalid JSON string
    test_event = {
        'type': 'test_event',
        'payload': '{invalid json here}'
    }
    mock_socket.recvfrom.return_value = (json.dumps(test_event).encode('utf-8'), None)
    
    await engine._check_control_socket()
    
    stored_event = engine.context.get('event_data')
    assert stored_event['payload'] == {}
    
    # Check warning was logged
    assert any('Invalid JSON payload' in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_empty_string_payload():
    """Empty string payload becomes empty dict"""
    engine = StateMachineEngine('test_machine')
    
    engine.config = {
        'initial_state': 'waiting',
        'transitions': [],
        'actions': {}
    }
    engine.current_state = 'waiting'
    
    mock_socket = MagicMock()
    engine.control_socket = mock_socket
    
    test_event = {
        'type': 'test_event',
        'payload': ''
    }
    mock_socket.recvfrom.return_value = (json.dumps(test_event).encode('utf-8'), None)
    
    await engine._check_control_socket()
    
    stored_event = engine.context.get('event_data')
    assert stored_event['payload'] == {}


@pytest.mark.asyncio
async def test_whitespace_payload():
    """Whitespace-only payload becomes empty dict"""
    engine = StateMachineEngine('test_machine')
    
    engine.config = {
        'initial_state': 'waiting',
        'transitions': [],
        'actions': {}
    }
    engine.current_state = 'waiting'
    
    mock_socket = MagicMock()
    engine.control_socket = mock_socket
    
    test_event = {
        'type': 'test_event',
        'payload': '   \n  '
    }
    mock_socket.recvfrom.return_value = (json.dumps(test_event).encode('utf-8'), None)
    
    await engine._check_control_socket()
    
    stored_event = engine.context.get('event_data')
    assert stored_event['payload'] == {}


@pytest.mark.asyncio
async def test_nested_json_not_recursively_parsed():
    """Nested JSON strings are not recursively parsed"""
    engine = StateMachineEngine('test_machine')
    
    engine.config = {
        'initial_state': 'waiting',
        'transitions': [],
        'actions': {}
    }
    engine.current_state = 'waiting'
    
    mock_socket = MagicMock()
    engine.control_socket = mock_socket
    
    # Outer JSON with inner JSON as escaped string
    test_event = {
        'type': 'test_event',
        'payload': '{"inner": "{\\"nested\\": \\"value\\"}"}'
    }
    mock_socket.recvfrom.return_value = (json.dumps(test_event).encode('utf-8'), None)
    
    await engine._check_control_socket()
    
    stored_event = engine.context.get('event_data')
    assert isinstance(stored_event['payload'], dict)
    assert isinstance(stored_event['payload']['inner'], str)  # Inner remains string
    assert stored_event['payload']['inner'] == '{"nested": "value"}'


@pytest.mark.asyncio
async def test_missing_payload_field():
    """Events without payload field don't cause errors"""
    engine = StateMachineEngine('test_machine')
    
    engine.config = {
        'initial_state': 'waiting',
        'transitions': [],
        'actions': {}
    }
    engine.current_state = 'waiting'
    
    mock_socket = MagicMock()
    engine.control_socket = mock_socket
    
    # No payload field
    test_event = {
        'type': 'test_event'
    }
    mock_socket.recvfrom.return_value = (json.dumps(test_event).encode('utf-8'), None)
    
    await engine._check_control_socket()
    
    stored_event = engine.context.get('event_data')
    # Should have default empty dict
    assert stored_event is not None


@pytest.mark.asyncio
async def test_null_payload():
    """Null payload is handled gracefully"""
    engine = StateMachineEngine('test_machine')
    
    engine.config = {
        'initial_state': 'waiting',
        'transitions': [],
        'actions': {}
    }
    engine.current_state = 'waiting'
    
    mock_socket = MagicMock()
    engine.control_socket = mock_socket
    
    test_event = {
        'type': 'test_event',
        'payload': None
    }
    mock_socket.recvfrom.return_value = (json.dumps(test_event).encode('utf-8'), None)
    
    await engine._check_control_socket()
    
    stored_event = engine.context.get('event_data')
    # None stays as None (not parsed as string)
    assert stored_event['payload'] is None or stored_event['payload'] == {}


@pytest.mark.asyncio
async def test_large_payload_parsing(caplog):
    """Large payloads (100KB) parse successfully"""
    engine = StateMachineEngine('test_machine')
    
    engine.config = {
        'initial_state': 'waiting',
        'transitions': [],
        'actions': {}
    }
    engine.current_state = 'waiting'
    
    mock_socket = MagicMock()
    engine.control_socket = mock_socket
    
    # Create large payload
    large_data = 'x' * 100000
    test_event = {
        'type': 'test_event',
        'payload': json.dumps({'data': large_data})
    }
    mock_socket.recvfrom.return_value = (json.dumps(test_event).encode('utf-8'), None)
    
    await engine._check_control_socket()
    
    stored_event = engine.context.get('event_data')
    assert isinstance(stored_event['payload'], dict)
    assert len(stored_event['payload']['data']) == 100000
    
    # Just verify it parsed successfully (log checking is optional)
    # The fact that it's a dict with correct length proves parsing worked
