"""
Unified database queue checking action

IMPORTANT: Changes via Change Management, see CLAUDE.md

Supports both face_processing and pony_flux job types in a single unified action
"""
import logging
from typing import Dict, Any, Optional
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ..base import BaseAction
from statemachine_engine.database.models import get_job_model

logger = logging.getLogger(__name__)

class CheckDatabaseQueueAction(BaseAction):
    """
    Unified action to check database queue for jobs of any type
    Supports both face_processing and pony_flux job types
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.job_model = get_job_model()
        # Get job type from config, default to face_processing for backward compatibility
        self.job_type = config.get('job_type', 'face_processing')
        # Get machine type for concurrent architecture
        self.machine_type = config.get('machine_type', None)
    
    async def execute(self, context: Dict[str, Any]) -> str:
        """Check database queue for next job of specified type"""
        try:
            # First, fail any processing jobs with missing input files (for face_processing only)
            if self.job_type == 'face_processing':
                self._fail_jobs_with_missing_files()
            
            job = self.job_model.get_next_job(job_type=self.job_type, machine_type=self.machine_type)
            
            if job:
                # Extract data from JSON field (get_next_job() already parsed it)
                job_data = job.get('data', {})
                
                # Store job in context - data is already in the right format
                # Engine will propagate job_data to context automatically
                context['current_job'] = {
                    'id': job['job_id'],
                    'source_job_id': job.get('source_job_id'),
                    'job_type': job['job_type'],
                    'data': job_data  # Already parsed by JobModel.get_next_job()
                }
                
                # Store job model in context for job completion
                context['job_model'] = self.job_model
                
                machine_name = context.get('machine_name', 'unknown')
                logger.info(f"[{machine_name}] {job['job_type']} job {job['job_id']} retrieved from queue (data keys: {list(job_data.keys())})")
                
                return "new_job"
            else:
                return "no_jobs"
                
        except Exception as e:
            machine_name = context.get('machine_name', 'unknown')
            logger.error(f"[{machine_name}] Error checking database queue: {e}")
            return "error"
    
    def _fail_jobs_with_missing_files(self):
        """Mark processing jobs as failed when they reference non-existent files"""
        try:
            # Only clean up jobs for this machine type
            machine_type = self.config.get('machine_type')
            problem_jobs = self.job_model.get_processing_jobs_with_missing_files(machine_type)
            
            for job in problem_jobs:
                job_id = job['job_id']
                # get_processing_jobs_with_missing_files returns jobs with data already parsed
                job_data = job.get('data', {})
                input_path = job_data.get('input_image_path')
                
                # Additional safety check for None values
                if input_path is None:
                    machine_name = self.config.get('machine_type', 'unknown')
                    logger.warning(f"[{machine_name}] Skipping job {job_id} - no input image path")
                    continue
                    
                reason = f"Input file not found: {input_path}"
                
                machine_name = self.config.get('machine_type', 'unknown')
                logger.warning(f"[{machine_name}] Marking job {job_id} as failed - {reason}")
                self.job_model.fail_job(job_id, reason)
                
            if problem_jobs:
                machine_name = self.config.get('machine_type', 'unknown')
                logger.info(f"[{machine_name}] Marked {len(problem_jobs)} jobs with missing input files as failed")
                
        except Exception as e:
            machine_name = self.config.get('machine_type', 'unknown')
            logger.error(f"[{machine_name}] Error during job cleanup: {e}")