-- =============================================================================
-- TABLE: jobs
-- PURPOSE: Generic job queue and lifecycle management
-- CATEGORY: Generic (Engine-ready)
-- =============================================================================
-- USED BY ACTIONS:
--   - bash_action.py (core) - Job context substitution
--   - check_database_queue_action.py (core) - Queue polling
--   - check_events_action.py (core) - Job-related event checking
--   - generate_image_description_action.py (domain/ai) - Job data access
--   - create_face_job_action.py (domain/job_management) - Job creation
--   - update_job_prompt_action.py (domain/job_management) - Job updates
--   - append_prompts_action.py (domain/pipeline) - Prompt aggregation
--   - load_ideation_job_action.py (domain/ideator) - Ideation job loading
-- =============================================================================
-- SAMPLE QUERIES:
--   -- Get next pending job for specific machine
--   SELECT * FROM jobs
--   WHERE status = 'pending' AND machine_type = 'sdxl_generator'
--   ORDER BY created_at ASC LIMIT 1;
--
--   -- List all failed jobs in last 24 hours
--   SELECT job_id, error_message, created_at FROM jobs
--   WHERE status = 'failed'
--   AND created_at > datetime('now', '-1 day')
--   ORDER BY created_at DESC;
--
--   -- Count jobs by status
--   SELECT status, COUNT(*) as count FROM jobs GROUP BY status;
-- =============================================================================

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE NOT NULL,
    job_type TEXT NOT NULL,
    machine_type TEXT,
    source_job_id TEXT,
    data TEXT,
    result TEXT,
    priority INTEGER DEFAULT 5,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata TEXT
);

-- Indexes for job queries
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs (status);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs (created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_machine_type ON jobs (machine_type, status);
CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs (priority DESC, created_at ASC);
