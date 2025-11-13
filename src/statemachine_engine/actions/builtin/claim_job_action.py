"""
Claim job action - marks a pending job as processing

YAML Usage:
    actions:
      - type: claim_job
        job_id: "{current_job.id}"
        success: job_claimed
        already_claimed: job_taken
        error: claim_error
"""
import logging
from typing import Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ..base import BaseAction
from statemachine_engine.database.models import get_job_model

logger = logging.getLogger(__name__)


class ClaimJobAction(BaseAction):
    """
    Action to claim a pending job (mark as processing).
    
    Used in batch spawning to atomically claim jobs before starting workers.
    Prevents race conditions when multiple controllers compete for jobs.
    
    Config:
        job_id (str): Job ID to claim (supports variable interpolation)
        success (str): Event when job claimed successfully (default: "claimed")
        already_claimed (str): Event when job already taken (default: "already_claimed")
        error (str): Event on error (default: "error")
    
    Returns:
        Event name based on claim result
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.job_model = get_job_model()
        self.job_id_template = config.get('job_id')
        self.success_event = config.get('success', 'claimed')
        self.already_claimed_event = config.get('already_claimed', 'already_claimed')
        self.error_event = config.get('error', 'error')
        
        if not self.job_id_template:
            raise ValueError("claim_job action requires 'job_id' parameter")
    
    async def execute(self, context: Dict[str, Any]) -> str:
        """Claim the specified job"""
        try:
            # Get job_id (might be a template)
            job_id = self.job_id_template
            
            # Attempt to claim the job
            claimed = self.job_model.claim_job(job_id)
            
            machine_name = context.get('machine_name', 'unknown')
            
            if claimed:
                logger.info(f"[{machine_name}] Successfully claimed job {job_id}")
                return self.success_event
            else:
                logger.warning(f"[{machine_name}] Job {job_id} already claimed or not found")
                return self.already_claimed_event
                
        except Exception as e:
            machine_name = context.get('machine_name', 'unknown')
            logger.error(f"[{machine_name}] Error claiming job: {e}")
            return self.error_event
