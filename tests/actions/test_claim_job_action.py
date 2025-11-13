"""
Tests for ClaimJobAction
"""
import pytest
from unittest.mock import MagicMock, patch
from statemachine_engine.actions.builtin.claim_job_action import ClaimJobAction


class TestClaimJobAction:
    """Test ClaimJobAction functionality"""
    
    @pytest.fixture
    def mock_job_model(self):
        """Mock job model"""
        with patch('statemachine_engine.actions.builtin.claim_job_action.get_job_model') as mock:
            job_model = MagicMock()
            mock.return_value = job_model
            yield job_model
    
    @pytest.mark.asyncio
    async def test_claim_success(self, mock_job_model):
        """Test successfully claiming a job"""
        mock_job_model.claim_job.return_value = True
        
        action = ClaimJobAction({
            'job_id': 'job_123',
            'success': 'claimed',
            'already_claimed': 'taken',
            'error': 'failed'
        })
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'claimed'
        mock_job_model.claim_job.assert_called_once_with('job_123')
    
    @pytest.mark.asyncio
    async def test_job_already_claimed(self, mock_job_model):
        """Test when job is already claimed"""
        mock_job_model.claim_job.return_value = False
        
        action = ClaimJobAction({
            'job_id': 'job_123',
            'success': 'claimed',
            'already_claimed': 'taken'
        })
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'taken'
    
    @pytest.mark.asyncio
    async def test_default_events(self, mock_job_model):
        """Test default event names"""
        mock_job_model.claim_job.return_value = True
        
        action = ClaimJobAction({'job_id': 'job_123'})
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'claimed'  # Default success event
    
    @pytest.mark.asyncio
    async def test_variable_interpolation(self, mock_job_model):
        """Test job_id with variable interpolation (passed as-is)"""
        mock_job_model.claim_job.return_value = True
        
        # Template string - engine should interpolate before calling action
        action = ClaimJobAction({
            'job_id': '{current_job.job_id}',
            'success': 'claimed'
        })
        context = {}
        
        result = await action.execute(context)
        
        # Action receives the template as-is (engine does interpolation)
        assert result == 'claimed'
        mock_job_model.claim_job.assert_called_once_with('{current_job.job_id}')
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_job_model):
        """Test error handling"""
        mock_job_model.claim_job.side_effect = Exception("Database error")
        
        action = ClaimJobAction({
            'job_id': 'job_123',
            'error': 'db_error'
        })
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'db_error'
    
    @pytest.mark.asyncio
    async def test_missing_job_id(self):
        """Test that missing job_id raises ValueError"""
        with pytest.raises(ValueError, match="requires 'job_id'"):
            ClaimJobAction({})
    
    @pytest.mark.asyncio
    async def test_default_error_event(self, mock_job_model):
        """Test default error event name"""
        mock_job_model.claim_job.side_effect = Exception("Error")
        
        action = ClaimJobAction({'job_id': 'job_123'})
        context = {}
        
        result = await action.execute(context)
        
        assert result == 'error'  # Default error event
