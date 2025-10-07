-- =============================================================================
-- TABLE: realtime_events
-- PURPOSE: Real-time event streaming for WebSocket UI updates
-- CATEGORY: Generic (Engine-ready)
-- =============================================================================
-- USED BY COMPONENTS:
--   - engine.py - Logs state transitions and job events
--   - websocket_server.py - Polls for unconsumed events
--   - Web UI (app.js) - Receives real-time updates
-- =============================================================================
-- SAMPLE QUERIES:
--   -- Get unconsumed events for WebSocket broadcast
--   SELECT * FROM realtime_events
--   WHERE consumed = 0
--   ORDER BY created_at ASC;
--
--   -- Mark events as consumed after broadcast
--   UPDATE realtime_events
--   SET consumed = 1, consumed_at = CURRENT_TIMESTAMP
--   WHERE id <= 12345;
--
--   -- List recent state changes for machine
--   SELECT event_type, payload, created_at FROM realtime_events
--   WHERE machine_name = 'face_processor'
--   AND event_type = 'state_change'
--   ORDER BY created_at DESC LIMIT 10;
-- =============================================================================

CREATE TABLE IF NOT EXISTS realtime_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    consumed BOOLEAN DEFAULT 0,
    consumed_at TIMESTAMP
);

-- Indexes for real-time event streaming
CREATE INDEX IF NOT EXISTS idx_realtime_pending ON realtime_events (consumed, created_at);
CREATE INDEX IF NOT EXISTS idx_realtime_machine ON realtime_events (machine_name, created_at);
