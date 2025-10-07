"""
Machine Event Model - State Machine Event Management

Handles event lifecycle for state machines: create, poll, mark processed.
Supports event routing to specific target machines.

IMPORTANT: Changes via Change Management, see CLAUDE.md
"""
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from .base import Database

logger = logging.getLogger(__name__)

class MachineEventModel:
    """Model for machine event coordination"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def send_event(self, target_machine: str, event_type: str, 
                   job_id: str = None, payload: str = None, source_machine: str = None) -> int:
        """Send an event to a target machine"""
        with self.db._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO machine_events (source_machine, target_machine, event_type, job_id, payload)
                VALUES (?, ?, ?, ?, ?)
            """, (source_machine, target_machine, event_type, job_id, payload))
            conn.commit()
            return cursor.lastrowid
    
    def get_pending_events(self, machine_name: str) -> List[Dict[str, Any]]:
        """Get pending events for a specific machine"""
        with self.db._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM machine_events 
                WHERE target_machine = ? AND status = 'pending'
                ORDER BY created_at
            """, (machine_name,)).fetchall()
            return [dict(row) for row in rows]
    
    def mark_event_processed(self, event_id: int):
        """Mark an event as processed"""
        with self.db._get_connection() as conn:
            conn.execute("""
                UPDATE machine_events 
                SET status = 'processed', processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (event_id,))
            conn.commit()
    
    def list_events(self, target_machine: str = None, status: str = None, 
                    limit: int = 50) -> List[Dict[str, Any]]:
        """List events with optional filters"""
        with self.db._get_connection() as conn:
            query = "SELECT * FROM machine_events WHERE 1=1"
            params = []
            
            if target_machine:
                query += " AND target_machine = ?"
                params.append(target_machine)
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
