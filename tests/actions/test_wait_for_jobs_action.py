"""
Unit tests for WaitForJobsAction.

Tests the database polling action that waits for tracked jobs to complete.
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from statemachine_engine.actions.builtin import WaitForJobsAction


class TestWaitForJobsAction:
    """Test suite for WaitForJobsAction."""

    @pytest.mark.asyncio
    async def test_all_jobs_completed(self):
        """Test when all tracked jobs have completed."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'spawned_jobs',
            'poll_interval': 0.1,
            'success': 'all_jobs_complete'
        })
        
        context = {
            'spawned_jobs': ['1', '2', '3']
        }
        
        # Mock _get_job_statuses to return all completed
        with patch.object(action, '_get_job_statuses', return_value={
            '1': 'completed',
            '2': 'completed',
            '3': 'completed'
        }):
            result = await action.execute(context)
        
        assert result == 'all_jobs_complete'
        assert context['completed_jobs'] == ['1', '2', '3']
        assert context['failed_jobs'] == []
        assert context['pending_jobs'] == []

    @pytest.mark.asyncio
    async def test_some_jobs_failed(self):
        """Test when some jobs completed and some failed."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'spawned_jobs',
            'poll_interval': 0.1,
            'success': 'all_jobs_complete'
        })
        
        context = {
            'spawned_jobs': ['1', '2', '3']
        }
        
        # Mock _get_job_statuses to return mixed statuses
        with patch.object(action, '_get_job_statuses', return_value={
            '1': 'completed',
            '2': 'failed',
            '3': 'completed'
        }):
            result = await action.execute(context)
        
        assert result == 'all_jobs_complete'
        assert context['completed_jobs'] == ['1', '3']
        assert context['failed_jobs'] == ['2']
        assert context['pending_jobs'] == []

    @pytest.mark.asyncio
    async def test_still_pending(self):
        """Test when some jobs are still pending/processing."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'spawned_jobs',
            'poll_interval': 0.1,
            'pending': 'still_waiting'
        })
        
        context = {
            'spawned_jobs': ['1', '2', '3']
        }
        
        # Mock _get_job_statuses to return some pending
        with patch.object(action, '_get_job_statuses', return_value={
            '1': 'completed',
            '2': 'processing',
            '3': 'pending'
        }):
            result = await action.execute(context)
        
        assert result == 'still_waiting'
        assert context['completed_jobs'] == ['1']
        assert context['failed_jobs'] == []
        assert context['pending_jobs'] == ['2', '3']

    @pytest.mark.asyncio
    async def test_timeout_exceeded(self):
        """Test timeout when jobs don't complete in time."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'spawned_jobs',
            'poll_interval': 0.1,
            'timeout': 0.2,  # Very short timeout
            'timeout_event': 'check_timeout'
        })
        
        context = {
            'spawned_jobs': ['1', '2'],
            'wait_start_time': time.time() - 0.3  # Already exceeded timeout
        }
        
        # Mock _get_job_statuses to return pending (shouldn't be called due to timeout)
        with patch.object(action, '_get_job_statuses', return_value={
            '1': 'processing',
            '2': 'processing'
        }) as mock_statuses:
            result = await action.execute(context)
        
        # When timeout is exceeded with timeout_event, returns immediately
        assert result == 'check_timeout'
        # Job statuses are not queried or set when timeout_event is configured
        assert 'pending_jobs' not in context

    @pytest.mark.asyncio
    async def test_empty_job_list(self):
        """Test when tracked job list is empty."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'spawned_jobs',
            'poll_interval': 0.1,
            'success': 'all_jobs_complete'
        })
        
        context = {
            'spawned_jobs': []
        }
        
        result = await action.execute(context)
        
        # Should return no_jobs_tracked for empty list
        assert result == 'no_jobs_tracked'

    @pytest.mark.asyncio
    async def test_missing_tracked_jobs_key(self):
        """Test when tracked_jobs_key doesn't exist in context."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'nonexistent_key',
            'poll_interval': 0.1,
            'success': 'all_jobs_complete'
        })
        
        context = {}
        
        result = await action.execute(context)
        
        # Should handle gracefully
        assert result == 'no_jobs_tracked'

    @pytest.mark.asyncio
    async def test_default_poll_interval(self):
        """Test that default poll_interval is used."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'spawned_jobs',
            'success': 'all_jobs_complete'
        })
        
        assert action.poll_interval == 2

    @pytest.mark.asyncio
    async def test_default_timeout(self):
        """Test that default timeout is used."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'spawned_jobs',
            'success': 'all_jobs_complete'
        })
        
        assert action.timeout == 300

    @pytest.mark.asyncio
    async def test_wait_start_time_tracking(self):
        """Test that wait_start_time is tracked in context."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'spawned_jobs',
            'poll_interval': 0.1,
            'success': 'all_jobs_complete'
        })
        
        context = {
            'spawned_jobs': ['1']
        }
        
        start_time = time.time()
        with patch.object(action, '_get_job_statuses', return_value={'1': 'completed'}):
            await action.execute(context)
        
        # wait_start_time should have been set then deleted when all jobs complete
        assert 'wait_start_time' not in context  # Cleared after completion

    @pytest.mark.asyncio
    async def test_wait_start_time_set_on_first_call(self):
        """Test that wait_start_time is set on first call with pending jobs."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'spawned_jobs',
            'poll_interval': 0.1,
            'pending': 'still_waiting'
        })
        
        context = {
            'spawned_jobs': ['1']
        }
        
        start_time = time.time()
        with patch.object(action, '_get_job_statuses', return_value={'1': 'processing'}):
            await action.execute(context)
        
        assert 'wait_start_time' in context
        assert context['wait_start_time'] >= start_time
        assert context['wait_start_time'] <= time.time()

    @pytest.mark.asyncio
    async def test_job_status_categorization(self):
        """Test that jobs are correctly categorized by status."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'spawned_jobs',
            'poll_interval': 0.1,
            'success': 'all_jobs_complete',
            'pending': 'still_waiting'
        })
        
        context = {
            'spawned_jobs': ['1', '2', '3', '4', '5']
        }
        
        # Mock _get_job_statuses with various statuses
        with patch.object(action, '_get_job_statuses', return_value={
            '1': 'completed',
            '2': 'failed',
            '3': 'processing',
            '4': 'pending',
            '5': 'completed'
        }):
            result = await action.execute(context)
        
        # Some still pending, should return pending event
        assert result == 'still_waiting'
        assert set(context['completed_jobs']) == {'1', '5'}
        assert set(context['failed_jobs']) == {'2'}
        assert set(context['pending_jobs']) == {'3', '4'}

    @pytest.mark.asyncio
    async def test_custom_event_names(self):
        """Test using custom event names."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'spawned_jobs',
            'poll_interval': 0.1,
            'success': 'custom_success',
            'pending': 'custom_pending',
            'timeout_event': 'custom_timeout'
        })
        
        context = {
            'spawned_jobs': ['1']
        }
        
        # Mock _get_job_statuses to return pending
        with patch.object(action, '_get_job_statuses', return_value={'1': 'processing'}):
            result = await action.execute(context)
        
        assert result == 'custom_pending'

    @pytest.mark.asyncio
    async def test_job_not_found_in_database(self):
        """Test handling of jobs not found in database."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'spawned_jobs',
            'poll_interval': 0.1,
            'pending': 'still_waiting'
        })
        
        context = {
            'spawned_jobs': ['1', '2', '3']
        }
        
        # Mock _get_job_statuses - job '3' not in results (not found)
        with patch.object(action, '_get_job_statuses', return_value={
            '1': 'completed',
            '2': 'completed'
            # '3' missing - should be treated as pending
        }):
            result = await action.execute(context)
        
        assert result == 'still_waiting'
        assert context['pending_jobs'] == ['3']  # Missing job treated as pending

    @pytest.mark.asyncio
    async def test_timeout_without_timeout_event(self):
        """Test that timeout falls through to pending event if no timeout_event configured."""
        action = WaitForJobsAction({
            'tracked_jobs_key': 'spawned_jobs',
            'poll_interval': 0.1,
            'timeout': 0.2,
            'pending': 'still_waiting'
            # No timeout_event configured
        })
        
        context = {
            'spawned_jobs': ['1'],
            'wait_start_time': time.time() - 0.3  # Exceeded timeout
        }
        
        with patch.object(action, '_get_job_statuses', return_value={'1': 'processing'}):
            result = await action.execute(context)
        
        # Should return pending event since no timeout_event set
        assert result == 'still_waiting'
