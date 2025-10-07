"""Tests for LogAction (activity_log) - database-backed activity logging."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_activity_log_basic_message():
    """Test logging a basic activity message."""
    from statemachine_engine.actions.builtin import LogAction

    config = {
        'message': 'Test activity message',
        'level': 'info',
        'success': 'continue'
    }
    action = LogAction(config)

    context = {
        'current_job': {'id': 'test_job_001'},
        'machine_name': 'test_machine'
    }

    with patch('statemachine_engine.actions.builtin.log_action.get_machine_event_model') as mock_event:
        mock_model = MagicMock()
        mock_model.send_event.return_value = 123
        mock_event.return_value = mock_model

        result = await action.execute(context)

        assert result == 'continue'
        mock_model.send_event.assert_called_once()
        call_args = mock_model.send_event.call_args
        assert call_args[1]['target_machine'] == 'ui'
        assert call_args[1]['event_type'] == 'activity_log'
        assert call_args[1]['job_id'] == 'test_job_001'
        assert call_args[1]['source_machine'] == 'test_machine'


@pytest.mark.asyncio
async def test_activity_log_different_levels():
    """Test logging messages with different severity levels."""
    from statemachine_engine.actions.builtin import LogAction
    import json

    levels = ['info', 'success', 'error']
    context = {
        'current_job': {'id': 'test_job_002'},
        'machine_name': 'test_machine'
    }

    for level in levels:
        config = {
            'message': f'Test {level} message',
            'level': level,
            'success': 'continue'
        }
        action = LogAction(config)

        with patch('statemachine_engine.actions.builtin.log_action.get_machine_event_model') as mock_event:
            mock_model = MagicMock()
            mock_model.send_event.return_value = 123
            mock_event.return_value = mock_model

            result = await action.execute(context)
            assert result == 'continue'

            # Verify level was included in payload
            call_args = mock_model.send_event.call_args
            payload = json.loads(call_args[1]['payload'])
            assert payload['level'] == level


@pytest.mark.asyncio
async def test_activity_log_placeholder_substitution():
    """Test placeholder substitution in activity log messages."""
    from statemachine_engine.actions.builtin import LogAction
    import json

    config = {
        'message': 'Processing job {job_id} on machine {machine_name}',
        'level': 'info',
        'success': 'continue'
    }
    action = LogAction(config)

    context = {
        'current_job': {'id': 'test_job_003'},
        'machine_name': 'sdxl_generator'
    }

    with patch('statemachine_engine.actions.builtin.log_action.get_machine_event_model') as mock_event:
        mock_model = MagicMock()
        mock_model.send_event.return_value = 123
        mock_event.return_value = mock_model

        result = await action.execute(context)

        assert result == 'continue'

        # Verify message substitution
        call_args = mock_model.send_event.call_args
        payload = json.loads(call_args[1]['payload'])
        assert 'test_job_003' in payload['message']
        assert 'sdxl_generator' in payload['message']


@pytest.mark.asyncio
async def test_activity_log_without_job_id():
    """Test logging activity without job context."""
    from statemachine_engine.actions.builtin import LogAction

    config = {
        'message': 'System startup',
        'level': 'info',
        'success': 'continue'
    }
    action = LogAction(config)

    context = {
        'machine_name': 'controller'
    }

    with patch('statemachine_engine.actions.builtin.log_action.get_machine_event_model') as mock_event:
        mock_model = MagicMock()
        mock_model.send_event.return_value = 123
        mock_event.return_value = mock_model

        result = await action.execute(context)

        assert result == 'continue'

        # Verify job_id is None
        call_args = mock_model.send_event.call_args
        assert call_args[1]['job_id'] is None


@pytest.mark.asyncio
async def test_activity_log_error_level():
    """Test logging error-level activities."""
    from statemachine_engine.actions.builtin import LogAction
    import json

    config = {
        'message': 'Failed to process image: {error_message}',
        'level': 'error',
        'success': 'continue'
    }
    action = LogAction(config)

    context = {
        'current_job': {'id': 'test_job_004'},
        'machine_name': 'face_processor',
        'error_message': 'Invalid image format'
    }

    with patch('statemachine_engine.actions.builtin.log_action.get_machine_event_model') as mock_event:
        mock_model = MagicMock()
        mock_model.send_event.return_value = 123
        mock_event.return_value = mock_model

        result = await action.execute(context)

        assert result == 'continue'

        # Verify error level and message
        call_args = mock_model.send_event.call_args
        payload = json.loads(call_args[1]['payload'])
        assert payload['level'] == 'error'
        assert 'Invalid image format' in payload['message']


@pytest.mark.asyncio
async def test_activity_log_event_data_payload():
    """Test event_data.payload placeholder substitution."""
    from statemachine_engine.actions.builtin import LogAction
    import json

    config = {
        'message': 'Relaying completion for {event_data.payload.job_id}',
        'level': 'info',
        'success': 'continue'
    }
    action = LogAction(config)

    context = {
        'machine_name': 'controller',
        'event_data': {
            'event_name': 'face_job_done',
            'payload': {'job_id': 'job_12345'}
        }
    }

    with patch('statemachine_engine.actions.builtin.log_action.get_machine_event_model') as mock_event:
        mock_model = MagicMock()
        mock_model.send_event.return_value = 123
        mock_event.return_value = mock_model

        result = await action.execute(context)

        assert result == 'continue'

        # Verify event_data.payload substitution
        call_args = mock_model.send_event.call_args
        payload = json.loads(call_args[1]['payload'])
        assert 'job_12345' in payload['message']


@pytest.mark.asyncio
async def test_activity_log_error_handling():
    """Test error handling when send_event fails."""
    from statemachine_engine.actions.builtin import LogAction

    config = {
        'message': 'Test message',
        'level': 'info',
        'success': 'continue',
        'error': 'log_failed'
    }
    action = LogAction(config)

    context = {
        'current_job': {'id': 'test_job'},
        'machine_name': 'test_machine'
    }

    with patch('statemachine_engine.actions.builtin.log_action.get_machine_event_model') as mock_event:
        mock_model = MagicMock()
        mock_model.send_event.side_effect = Exception('Database error')
        mock_event.return_value = mock_model

        result = await action.execute(context)

        # Should return configured error event
        assert result == 'log_failed'
