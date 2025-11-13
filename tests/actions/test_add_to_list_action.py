"""
Unit tests for AddToListAction.

Tests the helper action that maintains lists in context, used for tracking
spawned job IDs and other collections.
"""

import pytest
from statemachine_engine.actions.builtin import AddToListAction


class TestAddToListAction:
    """Test suite for AddToListAction."""

    @pytest.mark.asyncio
    async def test_create_new_list_with_single_value(self):
        """Test creating a new list with initial value."""
        action = AddToListAction({
            'list_key': 'my_list',
            'value': 'item1'
        })
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'success'
        assert 'my_list' in context
        assert context['my_list'] == ['item1']

    @pytest.mark.asyncio
    async def test_append_to_existing_list(self):
        """Test appending to an existing list."""
        action = AddToListAction({
            'list_key': 'my_list',
            'value': 'item2'
        })
        context = {'my_list': ['item1']}
        
        result = await action.execute(context)
        
        assert result == 'success'
        assert context['my_list'] == ['item1', 'item2']

    @pytest.mark.asyncio
    async def test_default_list_key_is_items(self):
        """Test that default list_key is 'items'."""
        action = AddToListAction({
            'value': 'test_value'
        })
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'success'
        assert 'items' in context
        assert context['items'] == ['test_value']

    @pytest.mark.asyncio
    async def test_variable_interpolation(self):
        """Test that value supports variable interpolation."""
        action = AddToListAction({
            'list_key': 'job_ids',
            'value': '{job.id}'
        })
        context = {
            'job': {'id': 42}
        }
        
        result = await action.execute(context)
        
        assert result == 'success'
        assert context['job_ids'] == [42]  # Interpolation preserves numeric type

    @pytest.mark.asyncio
    async def test_nested_variable_interpolation(self):
        """Test interpolation with nested context values."""
        action = AddToListAction({
            'list_key': 'names',
            'value': '{user.profile.name}'
        })
        context = {
            'user': {'profile': {'name': 'Alice'}}
        }
        
        result = await action.execute(context)
        
        assert result == 'success'
        assert context['names'] == ['Alice']

    @pytest.mark.asyncio
    async def test_multiple_additions(self):
        """Test adding multiple items sequentially."""
        action1 = AddToListAction({'list_key': 'ids', 'value': '1'})
        action2 = AddToListAction({'list_key': 'ids', 'value': '2'})
        action3 = AddToListAction({'list_key': 'ids', 'value': '3'})
        
        context = {}
        await action1.execute(context)
        await action2.execute(context)
        await action3.execute(context)
        
        assert context['ids'] == ['1', '2', '3']

    @pytest.mark.asyncio
    async def test_error_when_key_exists_but_not_list(self):
        """Test that action fails when key exists but isn't a list."""
        action = AddToListAction({
            'list_key': 'my_key',
            'value': 'test'
        })
        context = {'my_key': 'not_a_list'}
        
        result = await action.execute(context)
        
        assert result == 'error'

    @pytest.mark.asyncio
    async def test_custom_success_event(self):
        """Test using custom success event name."""
        action = AddToListAction({
            'list_key': 'items',
            'value': 'test',
            'success': 'item_added'
        })
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'item_added'

    @pytest.mark.asyncio
    async def test_numeric_values(self):
        """Test adding numeric values to list."""
        action = AddToListAction({
            'list_key': 'numbers',
            'value': 42
        })
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'success'
        assert context['numbers'] == [42]

    @pytest.mark.asyncio
    async def test_interpolation_with_missing_variable(self):
        """Test that missing variables in template are handled gracefully."""
        action = AddToListAction({
            'list_key': 'items',
            'value': '{missing.variable}'
        })
        context = {}
        
        result = await action.execute(context)
        
        # Should still add the literal string if interpolation fails
        assert result == 'success'
        assert 'items' in context

    @pytest.mark.asyncio
    async def test_empty_context_creates_new_list(self):
        """Test creating list in completely empty context."""
        action = AddToListAction({
            'list_key': 'new_list',
            'value': 'first'
        })
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'success'
        assert context == {'new_list': ['first']}

    @pytest.mark.asyncio
    async def test_preserves_other_context_values(self):
        """Test that action doesn't modify unrelated context values."""
        action = AddToListAction({
            'list_key': 'my_list',
            'value': 'new_item'
        })
        context = {
            'other_key': 'other_value',
            'another_key': 123
        }
        
        result = await action.execute(context)
        
        assert result == 'success'
        assert context['other_key'] == 'other_value'
        assert context['another_key'] == 123
        assert context['my_list'] == ['new_item']
