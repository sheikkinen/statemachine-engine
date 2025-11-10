"""
Action to mark a job as completed in the database

Usage:
    actions:
      ready:
        - type: complete_job
          job_id: "{job_id}"  # Use context variable
          success: job_completed
          error: completion_failed
"""
import logging
from typing import Dict, Any

from ..base import BaseAction
from ...database.models import get_job_model
from ...utils.interpolation import interpolate_value

logger = logging.getLogger(__name__)

class CompleteJobAction(BaseAction):
    """
    Mark a job as completed in the database
    
    Config:
        job_id: Job ID to complete (supports variable interpolation like "{job_id}")
        success: Event to emit on success (default: "success")
        error: Event to emit on error (default: "error")
    
    YAML Usage:
        actions:
          ready:
            - type: complete_job
              job_id: "{job_id}"
              success: job_completed
              error: completion_failed
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.job_id_template = config.get('job_id', '{job_id}')
        self.job_model = get_job_model()
    
    async def execute(self, context: Dict[str, Any]) -> str:
        """Mark job as completed in database"""
        try:
            # Interpolate job_id from context using shared utility
            job_id = interpolate_value(self.job_id_template, context)
            
            # Check if interpolation failed (template still contains {})
            if not job_id or '{' in job_id:
                machine_name = context.get('machine_name', 'unknown')
                logger.error(f"[{machine_name}] CompleteJobAction: job_id is required or contains unresolved variables: {job_id}")
                return self.get_config_value('error', 'error')
            
            # Mark job as completed
            self.job_model.complete_job(job_id)
            
            machine_name = context.get('machine_name', 'unknown')
            logger.info(f"[{machine_name}] ✅ Job {job_id} marked as completed")
            
            return self.get_config_value('success', 'success')
            
        except Exception as e:
            machine_name = context.get('machine_name', 'unknown')
            logger.error(f"[{machine_name}] Error completing job: {e}")
            return self.get_config_value('error', 'error')

