"""
ClearEventsAction - Clear pending events of specific types

NEW COMPONENT - Clears stale events from the event queue

This action removes pending events of specified types from the machine event queue.
Useful for cleaning up stale coordination events that are no longer relevant, such as
clearing 'ready_for_next_job' events when a new job starts.

KEY FEATURES:
- Clear events by type and target machine
- Filter by pending status only
- Async execution compatible with state machine engine

EVENTS GENERATED:
- events_cleared: Events successfully cleared
- no_events_to_clear: No matching events found
"""
import logging
from typing import Dict, Any, List

from ..base import BaseAction
from statemachine_engine.database.models import get_machine_event_model

logger = logging.getLogger(__name__)


class ClearEventsAction(BaseAction):
    """
    Action to clear pending events of specific types from the event queue
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # event_types can be a single string or list of strings
        event_types = config.get('event_types', [])
        if isinstance(event_types, str):
            event_types = [event_types]
        self.event_types = event_types
        self.target_machine = config.get('target_machine')

    async def execute(self, context: Dict[str, Any]) -> str:
        """Clear pending events of specified types"""
        try:
            machine_name = self.get_machine_name(context)
            if not self.event_types:
                logger.warning(f"[{machine_name}] No event types specified for clearing")
                return self.get_config_value('success', 'no_events_to_clear')

            if not self.target_machine:
                logger.warning(f"[{machine_name}] No target machine specified for clearing events")
                return self.get_config_value('success', 'no_events_to_clear')

            event_model = get_machine_event_model()
            total_cleared = 0

            # Get all pending events for the target machine
            all_events = event_model.get_pending_events(self.target_machine)

            # Filter by event types and clear
            for event in all_events:
                if event['event_type'] in self.event_types:
                    event_model.mark_event_processed(event['id'])
                    total_cleared += 1
                    logger.debug(f"Cleared pending event: {event['event_type']} (ID: {event['id']})")

            if total_cleared > 0:
                logger.info(f"[{machine_name}] Cleared {total_cleared} pending events of types: {', '.join(self.event_types)}")
                logger.info(f"[{machine_name}] Target machine: {self.target_machine}")
                return self.get_config_value('success', 'events_cleared')
            else:
                logger.debug(f"[{machine_name}] No pending events found for types: {', '.join(self.event_types)}")
                return self.get_config_value('success', 'no_events_to_clear')

        except Exception as e:
            logger.error(f"[{machine_name}] Error clearing events: {e}")
            return 'error'
