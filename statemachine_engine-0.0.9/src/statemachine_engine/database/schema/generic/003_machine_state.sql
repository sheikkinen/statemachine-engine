-- =============================================================================
-- TABLE: machine_state
-- PURPOSE: Real-time machine monitoring and health tracking
-- CATEGORY: Generic (Engine-ready)
-- =============================================================================
-- USED BY ACTIONS:
--   - check_machine_state_action.py (core) - Health checks and monitoring
-- =============================================================================
-- USED BY COMPONENTS:
--   - engine.py - Updates current state on transitions
--   - cli.py - Machine status monitoring
--   - websocket_server.py - Real-time UI updates
-- =============================================================================
-- SAMPLE QUERIES:
--   -- Get all running machines
--   SELECT machine_name, current_state, last_activity FROM machine_state
--   WHERE last_activity > datetime('now', '-5 minutes')
--   ORDER BY last_activity DESC;
--
--   -- Check if specific machine is stuck
--   SELECT machine_name, current_state,
--          (julianday('now') - julianday(last_activity)) * 24 * 60 as minutes_idle
--   FROM machine_state
--   WHERE machine_name = 'sdxl_generator';
--
--   -- List machines by state
--   SELECT current_state, COUNT(*) as count
--   FROM machine_state
--   GROUP BY current_state;
-- =============================================================================

CREATE TABLE IF NOT EXISTS machine_state (
    machine_name TEXT PRIMARY KEY,
    current_state TEXT,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pid INTEGER,
    metadata TEXT
);

-- Indexes for machine monitoring
CREATE INDEX IF NOT EXISTS idx_machine_state_activity ON machine_state (last_activity);
