"""
Database Models Package - Generic state machine models

Generic database models extracted from face-changer project.
Domain-specific models are not included in this generic engine package.
"""

# Generic models (engine-ready)
from .base import Database
from .job import JobModel
from .machine_event import MachineEventModel
from .realtime_event import RealtimeEventModel
from .machine_state import MachineStateModel

__all__ = [
    'Database',
    'JobModel',
    'MachineEventModel',
    'RealtimeEventModel',
    'MachineStateModel',
]

# Global database instance (for backward compatibility)
_db_instance = None

def get_database() -> Database:
    """Get singleton database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance

def get_job_model() -> JobModel:
    """Get job model instance"""
    return JobModel(get_database())

def get_machine_event_model() -> MachineEventModel:
    """Get machine event model instance"""
    return MachineEventModel(get_database())

def get_realtime_event_model() -> RealtimeEventModel:
    """Get realtime event model instance"""
    return RealtimeEventModel(get_database())

def get_machine_state_model() -> MachineStateModel:
    """Get machine state model instance"""
    return MachineStateModel(get_database())
