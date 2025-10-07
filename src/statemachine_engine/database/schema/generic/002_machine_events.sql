-- =============================================================================
-- TABLE: machine_events
-- PURPOSE: Inter-machine event coordination and messaging
-- CATEGORY: Generic (Engine-ready)
-- =============================================================================
-- USED BY ACTIONS:
--   - check_events_action.py (core) - Poll for pending events
--   - send_event_action.py (core) - Create new events
--   - clear_events_action.py (core) - Mark events as processed
-- =============================================================================
-- USED BY MACHINES:
--   - sdxl_generator - Sends sdxl_job_done events to controller
--   - face_processor - Sends face_job_done events to controller
--   - controller - Receives events and relays to descriptor
--   - descriptor - Receives describe_image events from controller
-- =============================================================================
-- SAMPLE QUERIES:
--   -- Get pending events for specific machine
--   SELECT * FROM machine_events
--   WHERE target_machine = 'controller' AND status = 'pending'
--   ORDER BY created_at ASC;
--
--   -- List all events between two machines
--   SELECT event_type, payload, created_at FROM machine_events
--   WHERE source_machine = 'sdxl_generator'
--   AND target_machine = 'controller'
--   ORDER BY created_at DESC LIMIT 20;
--
--   -- Count events by type
--   SELECT event_type, status, COUNT(*) as count
--   FROM machine_events
--   GROUP BY event_type, status;
-- =============================================================================

CREATE TABLE IF NOT EXISTS machine_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_machine TEXT,
    target_machine TEXT NOT NULL,
    event_type TEXT NOT NULL,
    job_id TEXT,
    payload TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Indexes for event queries
CREATE INDEX IF NOT EXISTS idx_events_machine ON machine_events (target_machine, status);
CREATE INDEX IF NOT EXISTS idx_events_created ON machine_events (created_at);
