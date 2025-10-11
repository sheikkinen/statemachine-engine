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
    
    def log_event(self, machine_name: str, event_type: str, payload: Dict[str, Any]) -> Optional[int]:
        """Log a real-time event to the database
        
        Returns:
            Event ID if successful, None if failed
        """
        try:
            with self.db._get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO realtime_events (machine_name, event_type, payload)
                    VALUES (?, ?, ?)
                """, (machine_name, event_type, json.dumps(payload)))
                conn.commit()
                return cursor.lastrowid
        except json.JSONDecodeError as e:
            logger.error(f"Failed to serialize payload for event {event_type}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to log realtime event {event_type} for {machine_name}: {e}")
            return None
    
    def get_unconsumed_events(self, since_id: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """Get unconsumed events since the given ID
        
        Returns:
            List of events (may be empty if error or no events)
        """
        try:
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
                    try:
                        event = dict(row)
                        event['payload'] = json.loads(event['payload'])
                        events.append(event)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse payload for event {row['id']}: {e}")
                        continue
                return events
        except Exception as e:
            logger.error(f"Failed to get unconsumed events: {e}")
            return []
    
    def mark_events_consumed(self, event_ids: List[int]) -> bool:
        """Mark events as consumed
        
        Returns:
            True if successful, False otherwise
        """
        if not event_ids:
            return True
        
        try:
            with self.db._get_connection() as conn:
                placeholders = ','.join(['?' for _ in event_ids])
                conn.execute(f"""
                    UPDATE realtime_events
                    SET consumed = 1, consumed_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})
                """, event_ids)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to mark events as consumed: {e}")
            return False
    
    def cleanup_old_events(self, hours_old: int = 24) -> int:
        """Clean up old consumed events
        
        Returns:
            Number of events deleted, or -1 if error
        """
        try:
            with self.db._get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM realtime_events
                    WHERE consumed = 1
                    AND consumed_at < datetime('now', '-{} hours')
                """.format(hours_old))
                deleted_count = cursor.rowcount
                conn.commit()
                logger.info(f"Cleaned up {deleted_count} old realtime events")
                return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old events: {e}")
            return -1
