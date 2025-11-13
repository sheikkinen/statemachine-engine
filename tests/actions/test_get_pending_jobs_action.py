"""
Tests for GetPendingJobsAction
"""
import pytest
from unittest.mock import MagicMock, patch
from statemachine_engine.actions.builtin.get_pending_jobs_action import GetPendingJobsAction


class TestGetPendingJobsAction:
    """Test GetPendingJobsAction functionality"""
    
    @pytest.fixture
    def mock_job_model(self):
        """Mock job model"""
        with patch('statemachine_engine.actions.builtin.get_pending_jobs_action.get_job_model') as mock:
            job_model = MagicMock()
            mock.return_value = job_model
            yield job_model
    
    @pytest.mark.asyncio
    async def test_get_jobs_success(self, mock_job_model):
        """Test getting pending jobs successfully"""
        # Mock job data
        mock_jobs = [
            {'job_id': 'job_001', 'status': 'pending', 'data': {'test': 1}},
            {'job_id': 'job_002', 'status': 'pending', 'data': {'test': 2}},
        ]
        mock_job_model.get_pending_jobs.return_value = mock_jobs
        
        action = GetPendingJobsAction({
            'job_type': 'test_job',
            'store_as': 'my_jobs',
            'success': 'found',
            'empty': 'none'
        })
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'found'
        assert context['my_jobs'] == mock_jobs
        assert len(context['my_jobs']) == 2
        mock_job_model.get_pending_jobs.assert_called_once_with(
            job_type='test_job',
            machine_type=None,
            limit=None
        )
    
    @pytest.mark.asyncio
    async def test_no_jobs(self, mock_job_model):
        """Test when no jobs are found"""
        mock_job_model.get_pending_jobs.return_value = []
        
        action = GetPendingJobsAction({
            'job_type': 'test_job',
            'success': 'found',
            'empty': 'none_found'
        })
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'none_found'
        assert context['pending_jobs'] == []  # Default store_as
    
    @pytest.mark.asyncio
    async def test_with_limit(self, mock_job_model):
        """Test getting jobs with limit"""
        mock_jobs = [
            {'job_id': 'job_001', 'status': 'pending'},
            {'job_id': 'job_002', 'status': 'pending'},
        ]
        mock_job_model.get_pending_jobs.return_value = mock_jobs
        
        action = GetPendingJobsAction({
            'job_type': 'test_job',
            'limit': 2,
            'success': 'found',
            'empty': 'none'
        })
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'found'
        mock_job_model.get_pending_jobs.assert_called_once_with(
            job_type='test_job',
            machine_type=None,
            limit=2
        )
    
    @pytest.mark.asyncio
    async def test_with_machine_type(self, mock_job_model):
        """Test filtering by machine type"""
        mock_jobs = [{'job_id': 'job_001', 'machine_type': 'worker1'}]
        mock_job_model.get_pending_jobs.return_value = mock_jobs
        
        action = GetPendingJobsAction({
            'job_type': 'test_job',
            'machine_type': 'worker1',
            'success': 'found',
            'empty': 'none'
        })
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'found'
        mock_job_model.get_pending_jobs.assert_called_once_with(
            job_type='test_job',
            machine_type='worker1',
            limit=None
        )
    
    @pytest.mark.asyncio
    async def test_default_events(self, mock_job_model):
        """Test default success/empty event names"""
        mock_job_model.get_pending_jobs.return_value = [{'job_id': '001'}]
        
        action = GetPendingJobsAction({})
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'jobs_found'  # Default success event
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_job_model):
        """Test error handling"""
        mock_job_model.get_pending_jobs.side_effect = Exception("Database error")
        
        action = GetPendingJobsAction({
            'success': 'found',
            'empty': 'none'
        })
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'error'
        assert context['pending_jobs'] == []
