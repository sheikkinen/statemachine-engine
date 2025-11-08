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
