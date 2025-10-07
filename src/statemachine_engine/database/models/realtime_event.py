"""
Realtime Event Model - WebSocket Event Streaming

Manages real-time events for WebSocket streaming.
Used by websocket_server.py for live UI updates.

IMPORTANT: Changes via Change Management, see CLAUDE.md
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from .base import Database

logger = logging.getLogger(__name__)

class RealtimeEventModel:
    """Model for real-time event logging and consumption"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def log_event(self, machine_name: str, event_type: str, payload: Dict[str, Any]) -> int:
        """Log a real-time event to the database"""
        with self.db._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO realtime_events (machine_name, event_type, payload)
                VALUES (?, ?, ?)
            """, (machine_name, event_type, json.dumps(payload)))
            conn.commit()
            return cursor.lastrowid
    
    def get_unconsumed_events(self, since_id: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Get unconsumed events since the given ID"""
        with self.db._get_connection() as conn:
            rows = conn.execute("""
                SELECT id, machine_name, event_type, payload, created_at
                FROM realtime_events
                WHERE id > ? AND consumed = 0
                ORDER BY id
                LIMIT ?
            """, (since_id, limit)).fetchall()
            
            events = []
            for row in rows:
                event = dict(row)
                event['payload'] = json.loads(event['payload'])
                events.append(event)
            return events
    
    def mark_events_consumed(self, event_ids: List[int]):
        """Mark events as consumed"""
        if not event_ids:
            return
        
        with self.db._get_connection() as conn:
            placeholders = ','.join(['?' for _ in event_ids])
            conn.execute(f"""
                UPDATE realtime_events
                SET consumed = 1, consumed_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
            """, event_ids)
            conn.commit()
    
    def cleanup_old_events(self, hours_old: int = 24):
        """Clean up old consumed events"""
        with self.db._get_connection() as conn:
            conn.execute("""
                DELETE FROM realtime_events
                WHERE consumed = 1
                AND consumed_at < datetime('now', '-{} hours')
            """.format(hours_old))
            conn.commit()
