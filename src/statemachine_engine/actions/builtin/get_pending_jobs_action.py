"""
Get pending jobs action - retrieves multiple jobs from queue without claiming them

YAML Usage:
    actions:
      - type: get_pending_jobs
        job_type: "pony_flux"
        machine_type: "{machine_type}"
        limit: 10  # optional, default: all
        store_as: "pending_jobs"
        success: jobs_found
        empty: no_jobs
"""
import logging
from typing import Dict, Any
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ..base import BaseAction
from statemachine_engine.database.models import get_job_model

logger = logging.getLogger(__name__)


class GetPendingJobsAction(BaseAction):
    """
    Action to retrieve multiple pending jobs from database queue.
    
    Unlike check_database_queue, this action:
    - Returns ALL pending jobs (or up to limit)
    - Does NOT mark jobs as processing
    - Stores jobs in context list for batch processing
    
    Config:
        job_type (str): Filter by job type (optional)
        machine_type (str): Filter by machine type (optional)
        limit (int): Max jobs to retrieve (optional, default: all)
        store_as (str): Context key to store jobs (default: "pending_jobs")
        success (str): Event to return when jobs found (default: "jobs_found")
        empty (str): Event to return when no jobs (default: "no_jobs")
    
    Returns:
        Event name based on whether jobs were found
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.job_model = get_job_model()
        self.job_type = config.get('job_type')
        self.machine_type = config.get('machine_type')
        self.limit = config.get('limit')
        self.store_as = config.get('store_as', 'pending_jobs')
        self.success_event = config.get('success', 'jobs_found')
        self.empty_event = config.get('empty', 'no_jobs')
    
    async def execute(self, context: Dict[str, Any]) -> str:
        """Retrieve pending jobs and store in context"""
        try:
            jobs = self.job_model.get_pending_jobs(
                job_type=self.job_type,
                machine_type=self.machine_type,
                limit=self.limit
            )
            
            if jobs:
                # Store jobs list in context
                context[self.store_as] = jobs
                
                machine_name = context.get('machine_name', 'unknown')
                logger.info(f"[{machine_name}] Retrieved {len(jobs)} pending jobs")
                
                return self.success_event
            else:
                # Clear the list if no jobs
                context[self.store_as] = []
                
                machine_name = context.get('machine_name', 'unknown')
                logger.info(f"[{machine_name}] No pending jobs found")
                
                return self.empty_event
                
        except Exception as e:
            machine_name = context.get('machine_name', 'unknown')
            logger.error(f"[{machine_name}] Error getting pending jobs: {e}")
            context[self.store_as] = []
            return "error"
