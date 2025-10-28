"""
Tests for timeout event functionality in StateMachineEngine
"""

import pytest
import asyncio
from statemachine_engine.core.engine import StateMachineEngine
from pathlib import Path
import tempfile
import yaml


@pytest.fixture
def timeout_config():
    """Create a temporary timeout test configuration"""
    config = {
        'name': 'Timeout Test Machine',
        'metadata': {'machine_name': 'timeout_test'},
        'initial_state': 'waiting',
        'states': ['waiting', 'timed_out', 'completed'],
        'events': ['initialized', 'timeout(1)', 'timeout(2)', 'manual_event', 'retry'],
        'transitions': [
            {'from': 'waiting', 'to': 'timed_out', 'event': 'timeout(1)'},
            {'from': 'waiting', 'to': 'completed', 'event': 'manual_event'},
            {'from': 'timed_out', 'to': 'waiting', 'event': 'retry'},
        ],
        'actions': {
            'waiting': [],
            'timed_out': [],
            'completed': [],
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        config_path = f.name
    
    yield config_path
    
    # Cleanup
    Path(config_path).unlink()


@pytest.mark.asyncio
async def test_timeout_fires_after_duration(timeout_config):
    """Test that timeout event fires after specified duration"""
    engine = StateMachineEngine(machine_name='timeout_test')
    await engine.load_config(timeout_config)
    
    # Start state machine in background
    task = asyncio.create_task(engine.execute_state_machine())
    
    # Wait for initialization
    await asyncio.sleep(0.1)
    assert engine.current_state == 'waiting'
    
    # Wait for timeout to fire (1 second + buffer)
    await asyncio.sleep(1.2)
    assert engine.current_state == 'timed_out'
    
    # Cleanup
    engine.is_running = False
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_timeout_cancelled_by_event(timeout_config):
    """Test that timeout is cancelled when another event arrives"""
    engine = StateMachineEngine(machine_name='timeout_test')
    await engine.load_config(timeout_config)
    
    # Start state machine in background
    task = asyncio.create_task(engine.execute_state_machine())
    
    # Wait for initialization
    await asyncio.sleep(0.1)
    assert engine.current_state == 'waiting'
    
    # Send manual event before timeout fires (timeout is 1 second)
    await asyncio.sleep(0.5)
    await engine.process_event('manual_event')
    
    # Verify we're in completed state, not timed_out
    assert engine.current_state == 'completed'
    
    # Wait past the original timeout duration
    await asyncio.sleep(0.7)
    
    # Should still be in completed state
    assert engine.current_state == 'completed'
    
    # Cleanup
    engine.is_running = False
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_timeout_restarts_on_state_change(timeout_config):
    """Test that timeout restarts when re-entering a state with timeout"""
    engine = StateMachineEngine(machine_name='timeout_test')
    await engine.load_config(timeout_config)
    
    # Start state machine in background
    task = asyncio.create_task(engine.execute_state_machine())
    
    # Wait for initialization
    await asyncio.sleep(0.1)
    assert engine.current_state == 'waiting'
    
    # Wait for first timeout
    await asyncio.sleep(1.2)
    assert engine.current_state == 'timed_out'
    
    # Return to waiting state
    await engine.process_event('retry')
    assert engine.current_state == 'waiting'
    
    # Wait for second timeout (should fire again)
    await asyncio.sleep(1.2)
    assert engine.current_state == 'timed_out'
    
    # Cleanup
    engine.is_running = False
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_multiple_timeout_transitions():
    """Test state with multiple timeout transitions (shortest fires first)"""
    config = {
        'name': 'Multiple Timeout Test',
        'metadata': {'machine_name': 'multi_timeout_test'},
        'initial_state': 'waiting',
        'states': ['waiting', 'short_timeout', 'long_timeout'],
        'events': ['timeout(0.5)', 'timeout(2)'],
        'transitions': [
            {'from': 'waiting', 'to': 'short_timeout', 'event': 'timeout(0.5)'},
            {'from': 'waiting', 'to': 'long_timeout', 'event': 'timeout(2)'},
        ],
        'actions': {
            'waiting': [],
            'short_timeout': [],
            'long_timeout': [],
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        config_path = f.name
    
    try:
        engine = StateMachineEngine(machine_name='multi_timeout_test')
        await engine.load_config(config_path)
        
        # Start state machine in background
        task = asyncio.create_task(engine.execute_state_machine())
        
        # Wait for initialization
        await asyncio.sleep(0.1)
        assert engine.current_state == 'waiting'
        
        # Wait for short timeout to fire (0.5s + buffer)
        await asyncio.sleep(0.7)
        assert engine.current_state == 'short_timeout'
        
        # Long timeout should not fire (was cancelled when short fired)
        await asyncio.sleep(1.5)
        assert engine.current_state == 'short_timeout'
        
        # Cleanup
        engine.is_running = False
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    finally:
        Path(config_path).unlink()


@pytest.mark.asyncio
async def test_timeout_parsing():
    """Test that timeout event syntax is correctly parsed"""
    engine = StateMachineEngine(machine_name='test')
    
    # Create minimal config
    engine.config = {
        'transitions': [
            {'from': 'waiting', 'to': 'done', 'event': 'timeout(5)'},
            {'from': 'waiting', 'to': 'done', 'event': 'timeout(10.5)'},
            {'from': 'processing', 'to': 'error', 'event': 'timeout(0.1)'},
        ]
    }
    
    # Get timeout transitions for waiting state
    timeouts = engine._get_timeout_transitions('waiting')
    
    assert len(timeouts) == 2
    assert timeouts[0]['duration'] == 5.0
    assert timeouts[0]['event_name'] == 'timeout(5)'
    assert timeouts[0]['to_state'] == 'done'
    
    assert timeouts[1]['duration'] == 10.5
    assert timeouts[1]['event_name'] == 'timeout(10.5)'
    assert timeouts[1]['to_state'] == 'done'
    
    # Get timeout transitions for processing state
    timeouts = engine._get_timeout_transitions('processing')
    assert len(timeouts) == 1
    assert timeouts[0]['duration'] == 0.1


@pytest.mark.asyncio
async def test_timeout_cleanup_on_shutdown(timeout_config):
    """Test that timeout tasks are cleaned up when engine shuts down"""
    engine = StateMachineEngine(machine_name='timeout_test')
    await engine.load_config(timeout_config)
    
    # Start state machine in background
    task = asyncio.create_task(engine.execute_state_machine())
    
    # Wait for initialization and timeout to start
    await asyncio.sleep(0.1)
    assert engine.current_state == 'waiting'
    assert len(engine.timeout_tasks) > 0
    
    # Shutdown engine
    engine.is_running = False
    
    # Wait for task to complete and cleanup to run
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except asyncio.TimeoutError:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # Verify timeout tasks are cleaned up
    assert len(engine.timeout_tasks) == 0
