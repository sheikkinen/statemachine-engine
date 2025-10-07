"""
Tests for BashAction fallback placeholder substitution
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from statemachine_engine.actions.builtin import BashAction


class TestBashActionFallback:
    """Test cases for fallback placeholder substitution in BashAction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.action_config = {
            'command': 'echo "prompt: {enhanced_prompt|pony_prompt}"',
            'timeout': 5
        }
        self.action = BashAction(self.action_config)
        
    @pytest.mark.asyncio
    async def test_fallback_uses_enhanced_prompt_when_available(self):
        """Test that fallback uses enhanced_prompt when it's available."""
        context = {
            'current_job': {
                'id': 'test_job_123',
                'data': {
                    'pony_prompt': 'beautiful woman',
                    'id': 'test_job_123'
                }
            },
            'enhanced_prompt': 'beautiful woman with stunning features, perfect lighting',
        }
        
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b'test output', b'')
            mock_subprocess.return_value = mock_process
            
            with patch('asyncio.wait_for') as mock_wait:
                mock_wait.return_value = (b'test output', b'')
                
                result = await self.action.execute(context)
                
                # Verify the command was called with enhanced prompt
                args, kwargs = mock_subprocess.call_args
                command = args[0]
                assert 'beautiful woman with stunning features, perfect lighting' in command
                assert result == 'job_done'
                
    @pytest.mark.asyncio
    async def test_fallback_uses_pony_prompt_when_enhanced_not_available(self):
        """Test that fallback uses pony_prompt when enhanced_prompt is not available."""
        context = {
            'current_job': {
                'id': 'test_job_123', 
                'data': {
                    'pony_prompt': 'beautiful woman',
                    'id': 'test_job_123'
                }
            }
            # No enhanced_prompt in context
        }
        
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b'test output', b'')
            mock_subprocess.return_value = mock_process
            
            with patch('asyncio.wait_for') as mock_wait:
                mock_wait.return_value = (b'test output', b'')
                
                result = await self.action.execute(context)
                
                # Verify the command was called with pony prompt (fallback)
                args, kwargs = mock_subprocess.call_args
                command = args[0]
                assert 'beautiful woman' in command
                assert result == 'job_done'
                
    @pytest.mark.asyncio
    async def test_fallback_handles_quoted_placeholders(self):
        """Test that fallback works with quoted placeholders."""
        self.action.config['command'] = "echo 'style_expl, {enhanced_prompt|pony_prompt}'"
        
        context = {
            'current_job': {
                'id': 'test_job_123',
                'data': {
                    'pony_prompt': 'beautiful woman',
                    'id': 'test_job_123'
                }
            },
            'enhanced_prompt': 'beautiful woman with perfect features',
        }
        
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b'test output', b'')
            mock_subprocess.return_value = mock_process
            
            with patch('asyncio.wait_for') as mock_wait:
                mock_wait.return_value = (b'test output', b'')
                
                result = await self.action.execute(context)
                
                # Verify the command was called correctly
                args, kwargs = mock_subprocess.call_args
                command = args[0]
                assert 'beautiful woman with perfect features' in command
                assert result == 'job_done'
                
    @pytest.mark.asyncio
    async def test_multiple_fallback_placeholders(self):
        """Test multiple fallback placeholders in the same command."""
        self.action.config['command'] = 'echo "{enhanced_prompt|pony_prompt}" and "{other_enhanced|other_fallback}"'
        
        context = {
            'current_job': {
                'id': 'test_job_123',
                'data': {
                    'pony_prompt': 'beautiful woman',
                    'other_fallback': 'fallback value',
                    'id': 'test_job_123'
                }
            },
            'enhanced_prompt': 'enhanced beautiful woman',
            # No other_enhanced in context, should use fallback
        }
        
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b'test output', b'')
            mock_subprocess.return_value = mock_process
            
            with patch('asyncio.wait_for') as mock_wait:
                mock_wait.return_value = (b'test output', b'')
                
                result = await self.action.execute(context)
                
                # Verify both substitutions worked
                args, kwargs = mock_subprocess.call_args
                command = args[0]
                assert 'enhanced beautiful woman' in command  # First placeholder used enhanced
                assert 'fallback value' in command  # Second placeholder used fallback
                assert result == 'job_done'
                
    @pytest.mark.asyncio
    async def test_regular_placeholders_still_work(self):
        """Test that regular placeholders continue to work alongside fallback syntax."""
        self.action.config['command'] = 'echo "{id}" "{enhanced_prompt|pony_prompt}"'
        
        context = {
            'current_job': {
                'id': 'test_job_123',
                'data': {
                    'pony_prompt': 'beautiful woman',
                    'id': 'test_job_123'
                }
            }
        }
        
        with patch('asyncio.create_subprocess_shell') as mock_subprocess:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b'test output', b'')
            mock_subprocess.return_value = mock_process
            
            with patch('asyncio.wait_for') as mock_wait:
                mock_wait.return_value = (b'test output', b'')
                
                result = await self.action.execute(context)
                
                # Verify both regular and fallback placeholders worked
                args, kwargs = mock_subprocess.call_args
                command = args[0]
                assert 'test_job_123' in command  # Regular placeholder
                assert 'beautiful woman' in command  # Fallback placeholder
                assert result == 'job_done'