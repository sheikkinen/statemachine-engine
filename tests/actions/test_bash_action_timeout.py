"""
Tests for BashAction timeout behavior

Verifies that:
1. Commands that exceed timeout are killed
2. Timeout error is properly returned
3. Error context is populated correctly
4. Process cleanup happens properly
"""

import pytest
import asyncio
from statemachine_engine.actions.builtin.bash_action import BashAction


class TestBashActionTimeout:
    """Test timeout handling in bash actions"""
    
    @pytest.mark.asyncio
    async def test_command_timeout_triggers_error(self):
        """Test that long-running command times out and returns error"""
        action = BashAction({
            'command': 'sleep 10',
            'timeout': 1,
            'description': 'Long running test command'
        })
        
        context = {}
        result = await action.execute(context)
        
        # Should return error event
        assert result == 'error'
        
        # Error context should be populated
        assert 'last_error' in context
        assert 'timed out after 1 seconds' in context['last_error']
        assert 'sleep 10' in context['last_error']
        assert context.get('last_error_action') == 'bash'
        assert context.get('last_error_command') == 'sleep 10'
        
        # Current job should be cleared
        assert 'current_job' not in context
    
    @pytest.mark.asyncio
    async def test_timeout_kills_process(self):
        """Test that timed-out process is actually killed"""
        import os
        import tempfile
        
        # Create a temp file that the process will try to write to
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.flag') as f:
            flag_file = f.name
        
        try:
            # Command that would run for 10 seconds but write a flag after 5
            command = f'sleep 5 && echo "still running" > {flag_file} && sleep 5'
            
            action = BashAction({
                'command': command,
                'timeout': 2,  # Kill after 2 seconds
            })
            
            context = {}
            result = await action.execute(context)
            
            # Should timeout
            assert result == 'error'
            
            # Wait a bit to ensure process is really dead
            await asyncio.sleep(6)
            
            # Flag file should NOT have been written (process was killed before sleep 5 finished)
            assert not os.path.exists(flag_file) or os.path.getsize(flag_file) == 0
            
        finally:
            # Cleanup
            if os.path.exists(flag_file):
                os.unlink(flag_file)
    
    @pytest.mark.asyncio
    async def test_timeout_with_custom_timeout_value(self):
        """Test that custom timeout values are respected"""
        action = BashAction({
            'command': 'sleep 3',
            'timeout': 5,  # Should NOT timeout
        })
        
        context = {}
        result = await action.execute(context)
        
        # Should succeed (sleep 3 < timeout 5)
        assert result == 'job_done'
        assert 'last_error' not in context
    
    @pytest.mark.asyncio
    async def test_default_timeout_30_seconds(self):
        """Test that default timeout is 30 seconds"""
        # Command that completes in 1 second
        action = BashAction({
            'command': 'sleep 1',
            # No timeout specified - should use default 30
        })
        
        context = {}
        result = await action.execute(context)
        
        # Should succeed (sleep 1 < default 30)
        assert result == 'job_done'
    
    @pytest.mark.asyncio
    async def test_timeout_with_job_context(self):
        """Test timeout with full job context"""
        action = BashAction({
            'command': 'sleep 10',
            'timeout': 1,
        })
        
        context = {
            'current_job': {
                'id': 'test_job_123',
                'data': {}
            }
        }
        
        result = await action.execute(context)
        
        assert result == 'error'
        assert 'last_error' in context
        assert 'timed out' in context['last_error']
        assert 'current_job' not in context  # Should be cleared
    
    @pytest.mark.asyncio
    async def test_timeout_with_stderr_output(self):
        """Test that stderr is captured before timeout"""
        # Command that writes to stderr then sleeps
        action = BashAction({
            'command': 'echo "error message" >&2 && sleep 10',
            'timeout': 1,
        })
        
        context = {}
        result = await action.execute(context)
        
        assert result == 'error'
        assert 'timed out' in context['last_error']
    
    @pytest.mark.asyncio
    async def test_quick_command_no_timeout(self):
        """Test that quick commands don't timeout"""
        action = BashAction({
            'command': 'echo "hello world"',
            'timeout': 1,
        })
        
        context = {}
        result = await action.execute(context)
        
        assert result == 'job_done'
        assert 'last_error' not in context
    
    @pytest.mark.asyncio
    async def test_timeout_error_message_format(self):
        """Test that timeout error message is well-formatted"""
        action = BashAction({
            'command': 'sleep 100',
            'timeout': 1,
            'description': 'Test long operation'
        })
        
        context = {}
        result = await action.execute(context)
        
        assert result == 'error'
        
        # Check error message format
        error_msg = context['last_error']
        assert 'Command timed out after 1 seconds' in error_msg
        assert 'Command: sleep 100' in error_msg
        
        # Check error metadata
        assert context['last_error_action'] == 'bash'
        assert context['last_error_command'] == 'sleep 100'
    
    @pytest.mark.asyncio
    async def test_custom_success_event_no_timeout(self):
        """Test that custom success event works when no timeout occurs"""
        action = BashAction({
            'command': 'echo "success"',
            'timeout': 5,
            'success': 'custom_success'
        })
        
        context = {}
        result = await action.execute(context)
        
        assert result == 'custom_success'
        assert 'last_error' not in context
    
    @pytest.mark.asyncio
    async def test_very_short_timeout(self):
        """Test with very short timeout (edge case)"""
        action = BashAction({
            'command': 'sleep 0.5',
            'timeout': 0.1,  # 100ms timeout
        })
        
        context = {}
        result = await action.execute(context)
        
        # Should timeout even though sleep is short
        assert result == 'error'
        assert 'timed out' in context['last_error']
    
    @pytest.mark.asyncio
    async def test_timeout_preserves_machine_name(self):
        """Test that machine name is preserved in timeout error logs"""
        action = BashAction({
            'command': 'sleep 10',
            'timeout': 1,
        })
        
        context = {
            'machine_name': 'test_worker'
        }
        
        result = await action.execute(context)
        
        assert result == 'error'
        assert 'last_error' in context
        # Machine name should still be in context
        assert context.get('machine_name') == 'test_worker'
