"""
LogAction - Log messages to the activity log (UI)

This action logs messages to the machine_events table so they appear
in the web UI's activity log. Useful for tracking state transitions
and important operations.
"""
import logging
import json
from typing import Dict, Any

from ..base import BaseAction
from statemachine_engine.database.models import get_machine_event_model

logger = logging.getLogger(__name__)

class LogAction(BaseAction):
    """
    Action to log messages that appear in the web UI activity log
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.message_template = config.get('message', 'Log message')
        self.level = config.get('level', 'info')  # info, error, success

    async def execute(self, context: Dict[str, Any]) -> str:
        """Log message to activity log"""
        try:
            event_model = get_machine_event_model()

            # Get machine name from context
            machine_name = context.get('machine_name', 'unknown')

            # Get job information from context
            current_job = context.get('current_job', {})
            job_id = current_job.get('id') if current_job else context.get('id')

            # Process message template with context substitution
            message = self._process_message(self.message_template, context)

            # Create payload with message and level
            payload = {
                'message': message,
                'level': self.level,
                'machine': machine_name
            }

            # Send event to UI - using target_machine 'ui' with event_type 'activity_log'
            event_id = event_model.send_event(
                target_machine='ui',
                event_type='activity_log',
                job_id=job_id,
                payload=json.dumps(payload),
                source_machine=machine_name
            )

            # Also log to Python logger
            log_func = getattr(logger, self.level, logger.info)
            log_func(f"Activity log: {message}")

            # Return success event
            success_event = self.get_config_value('success', 'continue')
            return success_event

        except Exception as e:
            logger.error(f"Error logging to activity log: {e}")
            return self.get_config_value('error', 'error')

    def _process_message(self, template: str, context: Dict[str, Any]) -> str:
        """Process message template with context substitution"""
        message = template

        # Get various context values
        current_job = context.get('current_job', {})
        job_id = current_job.get('id') if current_job else context.get('id')
        current_state = context.get('current_state', 'unknown')
        machine_name = context.get('machine_name', 'unknown')

        # Get event data
        event_data = context.get('event_data', {})
        event_name = event_data.get('event_name', '')
        event_payload = event_data.get('payload', {}) if event_data else {}

        # Standard substitutions
        substitutions = {
            '{id}': job_id or 'unknown',
            '{job_id}': job_id or 'unknown',
            '{current_state}': current_state,
            '{machine_name}': machine_name,
            '{event_name}': event_name
        }

        # Apply standard substitutions
        for placeholder, value in substitutions.items():
            if placeholder in message:
                message = message.replace(placeholder, str(value))

        # Handle event_data.payload.* substitutions
        if '{event_data.payload.' in message:
            import re
            pattern = r'\{event_data\.payload\.(\w+)\}'
            matches = re.findall(pattern, message)
            for key in matches:
                value = event_payload.get(key, f'{{event_data.payload.{key}}}')
                message = message.replace(f'{{event_data.payload.{key}}}', str(value))

        # Handle any remaining generic context variables
        if '{' in message:
            import re
            pattern = r'\{(\w+)\}'
            matches = re.findall(pattern, message)
            for key in matches:
                if key in context:
                    message = message.replace(f'{{{key}}}', str(context[key]))

        return message
