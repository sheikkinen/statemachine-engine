"""
Job Model - Generic Job Queue Management

Handles job lifecycle: create, fetch, update, complete, fail, delete.
Supports job chaining via source_job_id.

IMPORTANT: Changes via Change Management, see CLAUDE.md
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from pathlib import Path
from .base import Database

logger = logging.getLogger(__name__)

class JobModel:
    """Model for job management"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def create_job(self, job_id: str, job_type: str, machine_type: str = None,
                   source_job_id: str = None, priority: int = 5,
                   data: Dict[str, Any] = None, metadata: Dict[str, Any] = None) -> int:
        """
        Create a new job with JSON-based data storage.
        
        Args:
            job_id: Unique job identifier
            job_type: Type of job (e.g., 'face_processing', 'sdxl_generation')
            machine_type: Target machine name (optional)
            source_job_id: Parent job ID for chaining (optional)
            priority: Job priority (1=highest, 10=lowest, default=5)
            data: Domain-specific parameters as dict (stored as JSON)
                  Example: {'input_image_path': '/path/to/img.jpg', 
                           'user_prompt': 'make younger',
                           'padding_factor': 1.5}
            metadata: Additional metadata as dict (stored as JSON)
        
        Returns:
            Row ID of created job
        """
        with self.db._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO jobs (job_id, job_type, machine_type, source_job_id, 
                                 priority, data, metadata, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (
                job_id, 
                job_type, 
                machine_type, 
                source_job_id,
                priority,
                json.dumps(data) if data else None,
                json.dumps(metadata) if metadata else None
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_next_job(self, job_type: str = None, machine_type: str = None) -> Optional[Dict[str, Any]]:
        """
        Get next pending job with priority support and JSON parsing.
        
        Args:
            job_type: Filter by job type (optional)
            machine_type: Filter by assigned machine (optional)
                - If None: match ANY machine (enables controller to claim any job)
                - If specified: match ONLY jobs assigned to that machine
        
        Returns:
            Job dict with parsed JSON fields, or None if no jobs found
        """
        with self.db._get_connection() as conn:
            query = "SELECT * FROM jobs WHERE status = 'pending'"
            params = []
            
            if job_type:
                query += " AND job_type = ?"
                params.append(job_type)
            
            # Only filter by machine_type if explicitly provided (not None)
            if machine_type is not None:
                query += " AND machine_type = ?"
                params.append(machine_type)
            
            # Order by priority first (1=highest), then creation time
            query += " ORDER BY priority ASC, created_at ASC LIMIT 1"
            
            row = conn.execute(query, params).fetchone()
            
            if row:
                # Mark as processing
                conn.execute("""
                    UPDATE jobs 
                    SET status = 'processing', started_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                """, (row['job_id'],))
                conn.commit()
                
                # Convert to dict and parse JSON fields
                job = dict(row)
                # Update status in dict to reflect the database change
                job['status'] = 'processing'
                job['started_at'] = datetime.now().isoformat()
                if job.get('data'):
                    try:
                        job['data'] = json.loads(job['data'])
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse job data JSON for {job['job_id']}")
                        job['data'] = {}
                
                if job.get('result'):
                    try:
                        job['result'] = json.loads(job['result'])
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse job result JSON for {job['job_id']}")
                        job['result'] = {}
                
                if job.get('metadata'):
                    try:
                        job['metadata'] = json.loads(job['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse job metadata JSON for {job['job_id']}")
                        job['metadata'] = {}
                
                return job
            return None
    
    def get_latest_job_by_type(self, job_type: str) -> Optional[Dict[str, Any]]:
        """Get the most recent job of given type (for event validation)"""
        with self.db._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM jobs 
                WHERE job_type = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (job_type,)).fetchone()
            return dict(row) if row else None
    
    def complete_job(self, job_id: str):
        """Mark job as completed"""
        with self.db._get_connection() as conn:
            conn.execute("""
                UPDATE jobs 
                SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (job_id,))
            conn.commit()
    
    def fail_job(self, job_id: str, error_message: str):
        """Mark job as failed"""
        with self.db._get_connection() as conn:
            conn.execute("""
                UPDATE jobs 
                SET status = 'failed', error_message = ?, completed_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (error_message, job_id))
            conn.commit()
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID with JSON parsing"""
        with self.db._get_connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row:
                job = dict(row)
                # Parse JSON fields
                if job.get('data'):
                    try:
                        job['data'] = json.loads(job['data'])
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse job data JSON for {job_id}")
                        job['data'] = {}
                
                if job.get('result'):
                    try:
                        job['result'] = json.loads(job['result'])
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse job result JSON for {job_id}")
                        job['result'] = {}
                
                if job.get('metadata'):
                    try:
                        job['metadata'] = json.loads(job['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse job metadata JSON for {job_id}")
                        job['metadata'] = {}
                
                return job
            return None
    
    def list_jobs(self, status: Optional[str] = None, job_type: Optional[str] = None, 
                  machine_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """List jobs with optional status, job_type, and machine_type filters (parses JSON fields)"""
        with self.db._get_connection() as conn:
            query = "SELECT * FROM jobs WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if job_type:
                query += " AND job_type = ?"
                params.append(job_type)
            
            if machine_type:
                query += " AND machine_type = ?"
                params.append(machine_type)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            jobs = []
            for row in rows:
                job = dict(row)
                # Parse JSON fields
                if job.get('data'):
                    try:
                        job['data'] = json.loads(job['data'])
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse job data JSON for {job.get('job_id')}")
                        job['data'] = {}
                
                if job.get('result'):
                    try:
                        job['result'] = json.loads(job['result'])
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse job result JSON for {job.get('job_id')}")
                        job['result'] = {}
                
                if job.get('metadata'):
                    try:
                        job['metadata'] = json.loads(job['metadata'])
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse job metadata JSON for {job.get('job_id')}")
                        job['metadata'] = {}
                
                jobs.append(job)
            return jobs
    
    def count_jobs(self, status: Optional[str] = None, job_type: Optional[str] = None, machine_type: Optional[str] = None) -> int:
        """Count jobs by status, job_type, and/or machine_type"""
        with self.db._get_connection() as conn:
            query = "SELECT COUNT(*) FROM jobs WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if job_type:
                query += " AND job_type = ?"
                params.append(job_type)
            
            if machine_type:
                query += " AND machine_type = ?"
                params.append(machine_type)
            
            return conn.execute(query, params).fetchone()[0]
    
    def reset_job_to_pending(self, job_id: str, reason: str = "Reset to pending"):
        """Reset a specific job from processing back to pending"""
        with self.db._get_connection() as conn:
            conn.execute("""
                UPDATE jobs 
                SET status = 'pending', started_at = NULL, error_message = ?
                WHERE job_id = ? AND status = 'processing'
            """, (reason, job_id))
            conn.commit()
            logger.info(f"Reset job {job_id} to pending: {reason}")
    
    def get_processing_jobs_with_missing_files(self, machine_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find processing jobs that reference non-existent input files (checks data.input_image_path)"""
        with self.db._get_connection() as conn:
            query = "SELECT * FROM jobs WHERE status = 'processing'"
            params = []
            
            if machine_type:
                query += " AND machine_type = ?"
                params.append(machine_type)
                
            query += " ORDER BY started_at"
            
            rows = conn.execute(query, params).fetchall()
            
            problem_jobs = []
            for row in rows:
                job_dict = dict(row)
                # Parse JSON data field
                if job_dict.get('data'):
                    try:
                        data = json.loads(job_dict['data'])
                        input_path_str = data.get('input_image_path')
                        if input_path_str:
                            input_path = Path(input_path_str)
                            if not input_path.exists():
                                job_dict['data'] = data  # Include parsed data
                                problem_jobs.append(job_dict)
                    except (json.JSONDecodeError, TypeError):
                        logger.warning(f"Failed to parse data JSON for job {job_dict.get('job_id')}")
            
            return problem_jobs
    
    def store_pipeline_result(self, job_id: str, step_name: str, step_number: int = 0, metadata: str = None):
        """Store a pipeline result (used for state change logging)"""
        with self.db._get_connection() as conn:
            conn.execute("""
                INSERT INTO pipeline_results 
                (job_id, step_name, step_number, metadata)
                VALUES (?, ?, ?, ?)
            """, (job_id, step_name, step_number, metadata))
            conn.commit()
