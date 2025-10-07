"""
Machine State Model - State Machine Status Tracking

Provides convenient access to machine_state table.
Currently used by UI and CLI for status monitoring.

IMPORTANT: Changes via Change Management, see CLAUDE.md
"""
import json
import logging
from typing import Optional, Dict, List, Any
from .base import Database

logger = logging.getLogger(__name__)

class MachineStateModel:
    """Model for machine state tracking"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_all_machines(self) -> List[Dict[str, Any]]:
        """Get all machines with their current state"""
        with self.db._get_connection() as conn:
            rows = conn.execute("""
                SELECT machine_name, current_state, last_activity, metadata
                FROM machine_state ORDER BY machine_name
            """).fetchall()
            return [dict(row) for row in rows]
    
    def get_machine_state(self, machine_name: str) -> Optional[Dict[str, Any]]:
        """Get state for a specific machine"""
        with self.db._get_connection() as conn:
            row = conn.execute("""
                SELECT machine_name, current_state, last_activity, metadata
                FROM machine_state
                WHERE machine_name = ?
            """, (machine_name,)).fetchone()
            
            return dict(row) if row else None
    
    def update_machine_state(self, machine_name: str, current_state: str,
                            metadata: Dict[str, Any] = None):
        """Update or insert machine state"""
        with self.db._get_connection() as conn:
            conn.execute("""
                INSERT INTO machine_state (machine_name, current_state, metadata)
                VALUES (?, ?, ?)
                ON CONFLICT(machine_name) DO UPDATE SET
                    current_state = excluded.current_state,
                    last_activity = CURRENT_TIMESTAMP,
                    metadata = excluded.metadata
            """, (machine_name, current_state, json.dumps(metadata) if metadata else None))
            conn.commit()
    
    def get_recent_state_changes(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent state changes (from pipeline_results)"""
        with self.db._get_connection() as conn:
            rows = conn.execute("""
                SELECT 
                    json_extract(metadata, '$.machine') as machine_name,
                    json_extract(metadata, '$.state') as current_state,
                    json_extract(metadata, '$.event') as event,
                    completed_at as timestamp
                FROM pipeline_results 
                WHERE step_name = 'state_change'
                AND completed_at > datetime('now', '-' || ? || ' hour')
                ORDER BY completed_at DESC
            """, (hours,)).fetchall()
            
            return [dict(row) for row in rows]
