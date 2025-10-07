"""
Test bash action quote handling for complex prompts

Tests that bash action correctly handles:
- Parentheses in prompts
- Commas and special characters
- Double quotes in YAML commands
- Proper escaping for shell execution
"""
import pytest
import asyncio
import tempfile
import os
from statemachine_engine.actions.builtin import BashAction


class TestBashActionQuotes:
    """Test bash action quote handling with complex prompts"""

    @pytest.mark.asyncio
    async def test_prompt_with_parentheses_and_commas(self):
        """Test prompt with parentheses, commas, and special characters"""

        # Problematic prompt from tmp/shuf-1.txt
        test_prompt = "(Warrior carries a captive beauty in his arms). 1boy, 1girl, Bridal carry, eyes locked, one hand on chest, tension & devotion, kiss, nude,"

        # Test with single-quoted placeholder (corrected approach)
        config = {
            "command": "echo 'style_expl, '{pony_prompt} > {output_file}",
            "timeout": 10,
            "success": "success"
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            output_file = f.name

        try:
            context = {
                'current_job': {
                    'id': 'test_job_123',
                    'data': {
                        'pony_prompt': test_prompt,
                        'output_file': output_file
                    }
                }
            }

            action = BashAction(config)
            result = await action.execute(context)

            # Should succeed
            assert result == 'success'

            # Check output file was created
            assert os.path.exists(output_file)

            # Read the output and verify prompt was preserved
            with open(output_file, 'r') as f:
                content = f.read().strip()

            # Should contain the full prompt with all special characters
            assert '(Warrior carries a captive beauty in his arms)' in content
            assert '1boy, 1girl' in content
            assert 'tension & devotion' in content

        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

    @pytest.mark.asyncio
    async def test_prompt_with_quotes(self):
        """Test prompt containing double quotes"""

        test_prompt = 'A "beautiful" landscape with "amazing" details'

        config = {
            "command": "echo 'Prompt: '{pony_prompt} > {output_file}",
            "timeout": 10,
            "success": "success"
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            output_file = f.name

        try:
            context = {
                'current_job': {
                    'id': 'test_job_456',
                    'data': {
                        'pony_prompt': test_prompt,
                        'output_file': output_file
                    }
                }
            }

            action = BashAction(config)
            result = await action.execute(context)

            assert result == 'success'
            assert os.path.exists(output_file)

            with open(output_file, 'r') as f:
                content = f.read().strip()

            # Quotes should be preserved (or properly escaped)
            assert 'beautiful' in content
            assert 'amazing' in content

        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

    @pytest.mark.asyncio
    async def test_fallback_syntax_with_special_chars(self):
        """Test fallback syntax {enhanced_prompt|pony_prompt} with special characters"""

        pony_prompt = "(Special chars: & < > | ; $ ` \\ \" ')"
        enhanced_prompt = "Enhanced version"

        config = {
            "command": "echo '{enhanced_prompt|pony_prompt}' > {output_file}",
            "timeout": 10,
            "success": "success"
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            output_file = f.name

        try:
            # Test with enhanced_prompt available
            context = {
                'current_job': {
                    'id': 'test_job_789',
                    'data': {
                        'pony_prompt': pony_prompt,
                        'enhanced_prompt': enhanced_prompt,
                        'output_file': output_file
                    }
                },
                'enhanced_prompt': enhanced_prompt
            }

            action = BashAction(config)
            result = await action.execute(context)

            assert result == 'success'

            with open(output_file, 'r') as f:
                content = f.read().strip()

            # Should use enhanced_prompt (primary key)
            assert 'Enhanced version' in content

            # Now test fallback to pony_prompt
            os.remove(output_file)

            context_no_enhanced = {
                'current_job': {
                    'id': 'test_job_789',
                    'data': {
                        'pony_prompt': pony_prompt,
                        'output_file': output_file
                    }
                }
            }

            action2 = BashAction(config)
            result2 = await action2.execute(context_no_enhanced)

            assert result2 == 'success'

            with open(output_file, 'r') as f:
                content = f.read().strip()

            # Should contain pony_prompt with special chars
            assert 'Special chars' in content

        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

    @pytest.mark.asyncio
    async def test_actual_sdxl_command_format(self):
        """Test the actual command format used in sdxl_generator.yaml"""

        test_prompt = "(Warrior carries a captive beauty in his arms). 1boy, 1girl, Bridal carry"
        job_id = "sdxl_batch_test_001"

        # Simulate the fixed command from sdxl_generator.yaml line 251
        # Note: The actual command passes arguments to a script, not echo
        config = {
            "command": "echo '{enhanced_prompt|pony_prompt}' > {output_file}",
            "timeout": 10,
            "success": "success"
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            output_file = f.name

        try:
            context = {
                'current_job': {
                    'id': job_id,
                    'data': {
                        'pony_prompt': test_prompt,
                        'output_file': output_file
                    }
                }
            }

            action = BashAction(config)
            result = await action.execute(context)

            assert result == 'success'

            with open(output_file, 'r') as f:
                content = f.read().strip()

            # Verify prompt is properly quoted and contains special chars
            assert '(Warrior carries' in content or 'Warrior carries' in content
            assert '1boy' in content
            assert 'Bridal carry' in content

        finally:
            if os.path.exists(output_file):
                os.remove(output_file)
