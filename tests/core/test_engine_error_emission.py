"""
Tests for engine.py error emission to realtime_events
"""
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from statemachine_engine.core.engine import StateMachineEngine


@pytest.fixture
def engine():
    """Create a basic engine instance"""
    engine = StateMachineEngine(machine_name='test_machine')
    return engine


@pytest.fixture
def engine_with_context(engine):
    """Engine with job context"""
    engine.context = {
        'job_model': Mock(),
        'current_job': {
            'job_id': 'test_job_123',
            'data': {'test': 'data'}
        }
    }
    engine.context['job_model'].db = Mock()
    engine.context['job_model'].db._get_connection = Mock()
    return engine


def test_emit_error_basic(engine):
    """Test basic error emission"""
    with patch.object(engine, '_emit_realtime_event') as mock_emit:
        engine.emit_error('Test error message')
        
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args[0]
        assert call_args[0] == 'error'
        assert call_args[1]['error_message'] == 'Test error message'
        assert call_args[1]['job_id'] is None
        assert 'timestamp' in call_args[1]


def test_emit_error_with_job_id(engine):
    """Test error emission with job_id"""
    with patch.object(engine, '_emit_realtime_event') as mock_emit:
        engine.emit_error('Test error', job_id='job_456')
        
        call_args = mock_emit.call_args[0]
        assert call_args[1]['job_id'] == 'job_456'


def test_emit_job_started(engine):
    """Test job_started event emission"""
    with patch.object(engine, '_emit_realtime_event') as mock_emit:
        engine.emit_job_started('job_789', job_type='test_job')
        
        call_args = mock_emit.call_args[0]
        assert call_args[0] == 'job_started'
        assert call_args[1]['job_id'] == 'job_789'
        assert call_args[1]['job_type'] == 'test_job'


def test_emit_job_completed(engine):
    """Test job_completed event emission"""
    with patch.object(engine, '_emit_realtime_event') as mock_emit:
        engine.emit_job_completed('job_999', job_type='test_job')
        
        call_args = mock_emit.call_args[0]
        assert call_args[0] == 'job_completed'
        assert call_args[1]['job_id'] == 'job_999'


@pytest.mark.asyncio
async def test_execute_pluggable_action_not_found_emits_error(engine_with_context):
    """Test that missing action triggers error emission"""
    # Setup config
    engine_with_context.config = {'states': [], 'transitions': []}
    
    with patch('statemachine_engine.core.action_loader.ActionLoader') as mock_loader_class:
        mock_loader = Mock()
        mock_loader.load_action_class.return_value = None  # Action not found
        mock_loader_class.return_value = mock_loader
        
        with patch.object(engine_with_context, 'emit_error') as mock_emit_error:
            with patch.object(engine_with_context, 'process_event') as mock_process:
                action_config = {'type': 'nonexistent_action'}
                await engine_with_context._execute_pluggable_action('nonexistent_action', action_config)
                
                # Verify emit_error was called
                mock_emit_error.assert_called_once()
                error_msg = mock_emit_error.call_args[0][0]
                assert 'nonexistent_action' in error_msg
                assert 'not found' in error_msg
                
                # Verify error event was processed
                mock_process.assert_called_once_with('error')


@pytest.mark.asyncio
async def test_execute_pluggable_action_execution_error_emits_error(engine_with_context):
    """Test that action execution exception triggers error emission"""
    engine_with_context.config = {'states': [], 'transitions': []}
    
    # Mock action that raises exception
    mock_action = Mock()
    mock_action.execute = Mock(side_effect=Exception('Test exception'))
    
    mock_action_class = Mock(return_value=mock_action)
    
    with patch('statemachine_engine.core.action_loader.ActionLoader') as mock_loader_class:
        mock_loader = Mock()
        mock_loader.load_action_class.return_value = mock_action_class
        mock_loader_class.return_value = mock_loader
        
        with patch.object(engine_with_context, 'emit_error') as mock_emit_error:
            with patch.object(engine_with_context, 'process_event') as mock_process:
                action_config = {'type': 'failing_action'}
                await engine_with_context._execute_pluggable_action('failing_action', action_config)
                
                # Verify emit_error was called with job_id
                mock_emit_error.assert_called_once()
                error_msg = mock_emit_error.call_args[0][0]
                assert 'failing_action' in error_msg
                assert 'Test exception' in error_msg
                
                # Check job_id was passed
                job_id = mock_emit_error.call_args[1]['job_id']
                assert job_id == 'test_job_123'
                
                # Verify error event was processed
                mock_process.assert_called_once_with('error')


@pytest.mark.asyncio
async def test_execute_pluggable_action_loading_error_emits_error(engine_with_context):
    """Test that action loader exception triggers error emission"""
    engine_with_context.config = {'states': [], 'transitions': []}
    
    with patch('statemachine_engine.core.action_loader.ActionLoader') as mock_loader_class:
        mock_loader_class.side_effect = Exception('Loader initialization failed')
        
        with patch.object(engine_with_context, 'emit_error') as mock_emit_error:
            with patch.object(engine_with_context, 'process_event') as mock_process:
                action_config = {'type': 'test_action'}
                await engine_with_context._execute_pluggable_action('test_action', action_config)
                
                # Verify emit_error was called
                mock_emit_error.assert_called_once()
                error_msg = mock_emit_error.call_args[0][0]
                assert 'loading' in error_msg.lower()
                assert 'test_action' in error_msg


def test_emit_realtime_event_uses_socket_first(engine_with_context):
    """Test that _emit_realtime_event tries socket first"""
    with patch.object(engine_with_context.event_socket, 'emit', return_value=True) as mock_socket_emit:
        engine_with_context._emit_realtime_event('test_event', {'data': 'test'})
        
        # Should use socket
        mock_socket_emit.assert_called_once()
        call_args = mock_socket_emit.call_args[0][0]
        assert call_args['event_type'] == 'test_event'
        assert call_args['machine_name'] == 'test_machine'


@pytest.mark.skip(reason="Complex dynamic import path makes mocking difficult - tested via integration tests")
def test_emit_realtime_event_falls_back_to_database(engine_with_context):
    """Test database fallback when socket fails"""
    with patch.object(engine_with_context.event_socket, 'emit', return_value=False):
        with patch('statemachine_engine.database.models.get_realtime_event_model') as mock_get_model:
            mock_model = Mock()
            mock_get_model.return_value = mock_model
            
            engine_with_context._emit_realtime_event('test_event', {'data': 'test'})
            
            # Should fall back to database
            mock_model.log_event.assert_called_once()
            call_args = mock_model.log_event.call_args[0]
            assert call_args[0] == 'test_machine'
            assert call_args[1] == 'test_event'
            assert call_args[2] == {'data': 'test'}


def test_emit_realtime_event_handles_database_error(engine_with_context):
    """Test graceful handling of database logging error"""
    with patch.object(engine_with_context.event_socket, 'emit', return_value=False):
        with patch('statemachine_engine.database.models.get_realtime_event_model') as mock_get_model:
            mock_get_model.side_effect = Exception('Database error')
            
            # Should not raise exception
            try:
                engine_with_context._emit_realtime_event('test_event', {'data': 'test'})
            except Exception:
                pytest.fail("_emit_realtime_event should handle database errors gracefully")


def test_context_stores_last_error(engine):
    """Test that error context is stored"""
    engine.context = {}
    
    with patch.object(engine, '_emit_realtime_event'):
        with patch.object(engine, 'process_event'):
            engine.config = {'states': [], 'transitions': []}
            
            with patch('statemachine_engine.core.action_loader.ActionLoader') as mock_loader_class:
                mock_loader = Mock()
                mock_loader.load_action_class.return_value = None
                mock_loader_class.return_value = mock_loader
                
                asyncio.run(engine._execute_pluggable_action('missing_action', {'type': 'missing_action'}))
                
                # Verify context was updated
                assert 'last_error' in engine.context
                assert 'missing_action' in engine.context['last_error']
                assert engine.context['last_error_action'] == 'missing_action'
