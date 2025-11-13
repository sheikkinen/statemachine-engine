"""
WaitForJobsAction - Wait for tracked jobs to complete

Polls database to check if all tracked job IDs have reached terminal states
(completed or failed). Used by controller FSMs to wait for spawned workers
to finish before resuming job polling.

YAML Usage:
    actions:
      waiting_for_completion:
        - type: wait_for_jobs
          tracked_jobs_key: "spawned_jobs"  # Context key with list of job IDs
          poll_interval: 2                   # Seconds between checks (optional)
          timeout: 300                       # Max wait time (optional)
          success: all_jobs_complete         # All jobs done
          pending: still_waiting             # Jobs still processing
          timeout_event: check_timeout       # Timeout reached (optional)
"""
import logging
import time
from typing import Dict, Any, List

from ..base import BaseAction
from ...database.models import get_job_model

logger = logging.getLogger(__name__)


class WaitForJobsAction(BaseAction):
    """
    Wait for all tracked jobs to reach terminal states (completed/failed).
    
    Queries database for job statuses and returns appropriate event based on
    whether all jobs are done, some are still processing, or timeout reached.
    
    Config:
        tracked_jobs_key: Context key containing list of job IDs (default: "spawned_jobs")
        poll_interval: Seconds between status checks (default: 2)
        timeout: Maximum wait time in seconds (default: 300)
        success: Event when all jobs complete (default: "all_jobs_complete")
        pending: Event when jobs still processing (default: "still_waiting")
        timeout_event: Event when timeout reached (optional, uses pending if not set)
    
    Context Updates:
        completed_jobs: List of job IDs that completed successfully
        failed_jobs: List of job IDs that failed
        pending_jobs: List of job IDs still processing
        wait_start_time: Timestamp when waiting started (first call)
    
    Returns:
        - success event: All tracked jobs are completed or failed
        - pending event: Some jobs still processing
        - timeout_event: Timeout reached (if configured)
        - no_jobs_tracked: Empty or missing job list
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.tracked_jobs_key = config.get('tracked_jobs_key', 'spawned_jobs')
        self.poll_interval = config.get('poll_interval', 2)
        self.timeout = config.get('timeout', 300)
        self.job_model = get_job_model()
    
    async def execute(self, context: Dict[str, Any]) -> str:
        """Check status of all tracked jobs"""
        machine_name = context.get('machine_name', 'unknown')
        
        # Get tracked job IDs from context
        job_ids = context.get(self.tracked_jobs_key, [])
        
        if not job_ids:
            logger.warning(f"[{machine_name}] No jobs tracked in context key '{self.tracked_jobs_key}'")
            return 'no_jobs_tracked'
        
        # Track wait start time for timeout
        if 'wait_start_time' not in context:
            context['wait_start_time'] = time.time()
            logger.info(f"[{machine_name}] Starting to wait for {len(job_ids)} jobs: {job_ids}")
        
        # Check if timeout reached
        elapsed = time.time() - context['wait_start_time']
        if elapsed > self.timeout:
            logger.warning(f"[{machine_name}] Timeout reached after {elapsed:.1f}s waiting for jobs")
            timeout_event = self.config.get('timeout_event')
            if timeout_event:
                return timeout_event
            # Fall through to return pending event
        
        # Query database for job statuses
        statuses = self._get_job_statuses(job_ids)
        
        # Categorize jobs by status
        completed = []
        failed = []
        pending = []
        
        for job_id in job_ids:
            status = statuses.get(job_id)
            if status == 'completed':
                completed.append(job_id)
            elif status == 'failed':
                failed.append(job_id)
            elif status in ('pending', 'processing'):
                pending.append(job_id)
            else:
                # Job not found in database - treat as pending
                logger.warning(f"[{machine_name}] Job {job_id} not found in database")
                pending.append(job_id)
        
        # Update context with results
        context['completed_jobs'] = completed
        context['failed_jobs'] = failed
        context['pending_jobs'] = pending
        
        # Log status
        logger.info(
            f"[{machine_name}] Job status check: "
            f"completed={len(completed)}, failed={len(failed)}, pending={len(pending)}, "
            f"elapsed={elapsed:.1f}s"
        )
        
        # Check if all jobs are done
        if not pending:
            # Clear wait start time
            if 'wait_start_time' in context:
                del context['wait_start_time']
            
            logger.info(
                f"[{machine_name}] ✅ All jobs complete! "
                f"Success: {len(completed)}, Failed: {len(failed)}"
            )
            return self.config.get('success', 'all_jobs_complete')
        
        # Still have pending jobs - wait for timeout transition
        logger.info(f"[{machine_name}] ⏳ {len(pending)} jobs still processing...")
        pending_event = self.config.get('pending')
        if pending_event:
            return pending_event
        # If no pending event configured, return None to stay in current state
        # This allows timeout(N) transition to pace the polling
        return None
    
    def _get_job_statuses(self, job_ids: List[str]) -> Dict[str, str]:
        """
        Query database for status of all tracked jobs.
        
        Args:
            job_ids: List of job IDs to query
        
        Returns:
            Dictionary mapping job_id to status string
        """
        if not job_ids:
            return {}
        
        try:
            with self.job_model.db._get_connection() as conn:
                # Build query with proper number of placeholders
                placeholders = ','.join(['?'] * len(job_ids))
                query = f"""
                    SELECT job_id, status
                    FROM jobs
                    WHERE job_id IN ({placeholders})
                """
                
                rows = conn.execute(query, job_ids).fetchall()
                
                # Convert to dictionary
                return {row['job_id']: row['status'] for row in rows}
        
        except Exception as e:
            logger.error(f"Error querying job statuses: {e}")
            return {}
