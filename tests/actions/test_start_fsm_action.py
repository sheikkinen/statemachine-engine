"""
Tests for StartFsmAction - Spawn new FSM instances as separate processes

Following TDD approach:
- Phase 3.1 (RED): These tests should FAIL initially
- Phase 3.2 (GREEN): Implementation will make them PASS
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from statemachine_engine.actions.builtin.start_fsm_action import StartFsmAction


@pytest.mark.asyncio
async def test_start_fsm_basic_execution():
    """Test 1: Basic FSM spawning with minimal config"""
    config = {
        'yaml_path': '/path/to/worker.yaml',
        'machine_name': 'worker_001'
    }
    
    context = {
        'machine_name': 'controller',
        'id': 'controller_001'
    }
    
    with patch('subprocess.Popen') as mock_popen:
        # Mock process with PID
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        result = await action.execute(context)
        
        # Should return success event
        assert result == 'success'
        
        # Should call subprocess.Popen with correct command
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args == ['statemachine', '/path/to/worker.yaml', '--machine-name', 'worker_001']


@pytest.mark.asyncio
async def test_start_fsm_with_custom_success_event():
    """Test 2: Custom success event name"""
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_002',
        'success': 'worker_started'
    }
    
    context = {
        'machine_name': 'controller'
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12346
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        result = await action.execute(context)
        
        # Should return custom success event
        assert result == 'worker_started'


@pytest.mark.asyncio
async def test_start_fsm_with_variable_interpolation():
    """Test 3: Variable interpolation in machine_name"""
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_{job_id}'
    }
    
    context = {
        'machine_name': 'controller',
        'job_id': 'job_123'
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12347
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        result = await action.execute(context)
        
        # Should interpolate job_id into machine_name
        call_args = mock_popen.call_args[0][0]
        assert call_args[3] == 'worker_job_123'


@pytest.mark.asyncio
async def test_start_fsm_captures_pid():
    """Test 4: PID captured and stored in context"""
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_003',
        'store_pid': True
    }
    
    context = {
        'machine_name': 'controller',
        'spawned_pids': []
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 99999
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        result = await action.execute(context)
        
        # PID should be stored in context
        assert 'spawned_pids' in context
        assert 99999 in context['spawned_pids']


@pytest.mark.asyncio
async def test_start_fsm_missing_yaml_path():
    """Test 5: Error handling when yaml_path is missing"""
    config = {
        'machine_name': 'worker_004'
        # yaml_path is missing
    }
    
    context = {
        'machine_name': 'controller'
    }
    
    action = StartFsmAction(config)
    result = await action.execute(context)
    
    # Should return error event
    assert result == 'error'


@pytest.mark.asyncio
async def test_start_fsm_missing_machine_name():
    """Test 6: Error handling when machine_name is missing"""
    config = {
        'yaml_path': 'config/worker.yaml'
        # machine_name is missing
    }
    
    context = {
        'machine_name': 'controller'
    }
    
    action = StartFsmAction(config)
    result = await action.execute(context)
    
    # Should return error event
    assert result == 'error'


@pytest.mark.asyncio
async def test_start_fsm_subprocess_failure():
    """Test 7: Error handling when subprocess fails to start"""
    config = {
        'yaml_path': 'config/invalid.yaml',
        'machine_name': 'worker_005',
        'error': 'spawn_failed'
    }
    
    context = {
        'machine_name': 'controller'
    }
    
    with patch('subprocess.Popen') as mock_popen:
        # Simulate subprocess failure
        mock_popen.side_effect = FileNotFoundError("statemachine command not found")
        
        action = StartFsmAction(config)
        result = await action.execute(context)
        
        # Should return custom error event
        assert result == 'spawn_failed'


@pytest.mark.asyncio
async def test_start_fsm_with_additional_args():
    """Test 8: Additional command-line arguments passed to spawned FSM"""
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_006',
        'additional_args': ['--debug', '--log-level=INFO']
    }
    
    context = {
        'machine_name': 'controller'
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12348
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        result = await action.execute(context)
        
        # Should include additional args in command
        call_args = mock_popen.call_args[0][0]
        assert '--debug' in call_args
        assert '--log-level=INFO' in call_args


@pytest.mark.asyncio
async def test_start_fsm_process_is_detached():
    """Test 9: Spawned process runs in background (non-blocking)"""
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_007'
    }
    
    context = {
        'machine_name': 'controller'
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12349
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        result = await action.execute(context)
        
        # Should NOT call wait() or communicate() - process runs detached
        mock_process.wait.assert_not_called()
        mock_process.communicate.assert_not_called()
        
        # Should verify process was spawned
        mock_popen.assert_called_once()


@pytest.mark.asyncio
async def test_start_fsm_multiple_variable_interpolations():
    """Test 10: Multiple context variables in machine_name and yaml_path"""
    config = {
        'yaml_path': 'config/{job_type}_worker.yaml',
        'machine_name': 'worker_{job_type}_{job_id}'
    }
    
    context = {
        'machine_name': 'controller',
        'job_type': 'patient_records',
        'job_id': 'pr_456'
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12350
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        result = await action.execute(context)
        
        # Should interpolate both job_type and job_id
        call_args = mock_popen.call_args[0][0]
        assert call_args[1] == 'config/patient_records_worker.yaml'
        assert call_args[3] == 'worker_patient_records_pr_456'


@pytest.mark.asyncio
async def test_start_fsm_nested_variable_interpolation():
    """Test 11: Nested variable interpolation (current_job.id)"""
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_{current_job.id}'
    }
    
    context = {
        'machine_name': 'controller',
        'current_job': {
            'id': 'job_789',
            'type': 'patient_records'
        }
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12351
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        result = await action.execute(context)
        
        # Should interpolate nested path current_job.id
        call_args = mock_popen.call_args[0][0]
        assert call_args[3] == 'worker_job_789'


# ==============================================================================
# NEW TESTS: Context Passing Feature (Phase 3 - Context Passing)
# ==============================================================================

@pytest.mark.asyncio
async def test_start_fsm_with_context_vars():
    """Test 12: Basic context variable extraction and passing"""
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_001',
        'context_vars': ['job_id', 'report_id', 'report_title']
    }
    
    context = {
        'machine_name': 'controller',
        'job_id': 'job_001',
        'report_id': 'report_1',
        'report_title': 'Test Report'
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        result = await action.execute(context)
        
        # Should return success
        assert result == 'success'
        
        # Verify command includes --initial-context
        call_args = mock_popen.call_args[0][0]
        assert '--initial-context' in call_args
        
        # Parse and verify JSON context
        import json
        ctx_idx = call_args.index('--initial-context') + 1
        context_json = json.loads(call_args[ctx_idx])
        
        assert context_json == {
            'job_id': 'job_001',
            'report_id': 'report_1',
            'report_title': 'Test Report'
        }


@pytest.mark.asyncio
async def test_start_fsm_with_nested_context_vars():
    """Test 13: Nested variable extraction with dot notation"""
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_002',
        'context_vars': ['current_job.id', 'current_job.type', 'report_id']
    }
    
    context = {
        'machine_name': 'controller',
        'current_job': {
            'id': 'job_001',
            'type': 'patient_records'
        },
        'report_id': 'report_1'
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12346
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        result = await action.execute(context)
        
        # Verify command includes --initial-context
        call_args = mock_popen.call_args[0][0]
        assert '--initial-context' in call_args
        
        # Parse and verify nested extraction
        import json
        ctx_idx = call_args.index('--initial-context') + 1
        context_json = json.loads(call_args[ctx_idx])
        
        # Nested keys should be preserved (will be renamed with 'as' syntax)
        assert context_json['current_job.id'] == 'job_001'
        assert context_json['current_job.type'] == 'patient_records'
        assert context_json['report_id'] == 'report_1'


@pytest.mark.asyncio
async def test_start_fsm_with_renamed_context_vars():
    """Test 14: Variable renaming with 'as' syntax"""
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_003',
        'context_vars': [
            'current_job.id as job_id',
            'long_variable_name as short'
        ]
    }
    
    context = {
        'machine_name': 'controller',
        'current_job': {'id': 'job_001'},
        'long_variable_name': 'value123'
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12347
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        result = await action.execute(context)
        
        # Verify renamed keys in JSON context
        call_args = mock_popen.call_args[0][0]
        
        import json
        ctx_idx = call_args.index('--initial-context') + 1
        context_json = json.loads(call_args[ctx_idx])
        
        # Keys should be renamed
        assert context_json == {
            'job_id': 'job_001',
            'short': 'value123'
        }
        # Original keys should NOT exist
        assert 'current_job.id' not in context_json
        assert 'long_variable_name' not in context_json


@pytest.mark.asyncio
async def test_start_fsm_missing_context_vars():
    """Test 15: Graceful handling of missing context variables"""
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_004',
        'context_vars': ['existing_var', 'missing_var', 'also.missing']
    }
    
    context = {
        'machine_name': 'controller',
        'existing_var': 'value'
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12348
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        result = await action.execute(context)
        
        # Should succeed with partial context
        assert result == 'success'
        
        # Only existing var should be included
        call_args = mock_popen.call_args[0][0]
        
        import json
        ctx_idx = call_args.index('--initial-context') + 1
        context_json = json.loads(call_args[ctx_idx])
        
        assert context_json == {'existing_var': 'value'}
        assert 'missing_var' not in context_json
        assert 'also.missing' not in context_json


@pytest.mark.asyncio
async def test_start_fsm_empty_context_vars():
    """Test 16: No --initial-context arg when context_vars not specified"""
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_005'
        # No context_vars specified
    }
    
    context = {
        'machine_name': 'controller',
        'some': 'data'
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12349
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        await action.execute(context)
        
        # Verify no --initial-context arg added
        call_args = mock_popen.call_args[0][0]
        assert '--initial-context' not in call_args


@pytest.mark.asyncio
async def test_start_fsm_empty_context_vars_list():
    """Test 17: No --initial-context arg when context_vars is empty list"""
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_006',
        'context_vars': []  # Empty list
    }
    
    context = {
        'machine_name': 'controller',
        'some': 'data'
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12350
        mock_popen.return_value = mock_process
        
        action = StartFsmAction(config)
        await action.execute(context)
        
        # Verify no --initial-context arg added
        call_args = mock_popen.call_args[0][0]
        assert '--initial-context' not in call_args


@pytest.mark.asyncio
async def test_start_fsm_large_context_warning():
    """Test 18: Warning logged for large context (>4KB)"""
    config = {
        'yaml_path': 'config/worker.yaml',
        'machine_name': 'worker_007',
        'context_vars': ['large_data']
    }
    
    context = {
        'machine_name': 'controller',
        'large_data': 'x' * 5000  # >4KB
    }
    
    with patch('subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.pid = 12351
        mock_popen.return_value = mock_process
        
        # Capture log warnings
        with patch('statemachine_engine.actions.builtin.start_fsm_action.logger') as mock_logger:
            action = StartFsmAction(config)
            await action.execute(context)
            
            # Verify warning was logged
            mock_logger.warning.assert_called()
            warning_msg = str(mock_logger.warning.call_args[0][0])
            assert 'large' in warning_msg.lower() or 'bytes' in warning_msg.lower()

