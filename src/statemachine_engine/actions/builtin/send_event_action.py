"""
SendEventAction - Send events to other machines

IMPORTANT: Changes via Change Management, see CLAUDE.md

This action sends events to other machines for coordination in concurrent architecture.
Used to notify other machines about job completion, status changes, etc.
"""
import logging
import json
import socket
from pathlib import Path
from typing import Dict, Any

from ..base import BaseAction
from statemachine_engine.database.models import get_machine_event_model

logger = logging.getLogger(__name__)

class SendEventAction(BaseAction):
    """
    Action to send events to other machines for coordination
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.target_machine = config.get('target_machine', 'unknown')
        self.event_type = config.get('event_type', 'generic_event')
        self.payload_template = config.get('payload', {})
    
    async def execute(self, context: Dict[str, Any]) -> str:
        """Send event to target machine via Unix socket (with database fallback)"""
        try:
            # Get job information from context - support both formats
            current_job = context.get('current_job', {})
            job_id = current_job.get('id') if current_job else context.get('id')
            
            # Process payload template with context substitution
            payload = self._process_payload(self.payload_template, context)
            
            # Try fast path: Unix socket
            machine_name = context.get('machine_name', 'unknown')
            if self._send_via_socket(payload, job_id, machine_name):
                logger.info(f"[{machine_name}] Sent {self.event_type} to {self.target_machine} via Unix socket")
            else:
                # Fallback: Database (for audit trail and resilience)
                event_model = get_machine_event_model()
                payload_json = json.dumps(payload) if payload else None
                
                event_id = event_model.send_event(
                    target_machine=self.target_machine,
                    event_type=self.event_type,
                    job_id=job_id,
                    payload=payload_json
                )
                
                # Send wake-up signal via socket (fast path)
                self._send_wake_up_socket(machine_name)
                
                logger.info(f"[{machine_name}] Sent {self.event_type} to {self.target_machine} via database (event_id: {event_id})")
            
            if job_id:
                logger.debug(f"[{machine_name}] Event relates to job: {job_id}")
            
            if payload:
                logger.debug(f"[{machine_name}] Event payload: {payload}")
            
            # Return custom success event if specified, otherwise 'event_sent'
            success_event = self.get_config_value('success', 'event_sent')
            return success_event
            
        except Exception as e:
            machine_name = context.get('machine_name', 'unknown')
            logger.error(f"[{machine_name}] Error sending event: {e}")
            return 'error'
    
    def _send_wake_up_socket(self, machine_name: str = 'unknown') -> bool:
        """Send wake-up signal via Unix socket. Returns True if successful."""
        try:
            socket_path = f'/tmp/statemachine-control-{self.target_machine}.sock'
            
            # Check if socket exists
            if not Path(socket_path).exists():
                return False
            
            # Send wake-up message
            wake_up_msg = json.dumps({'type': 'wake_up'})
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.sendto(wake_up_msg.encode('utf-8'), socket_path)
            sock.close()
            
            logger.debug(f"[{machine_name}] 📤 Sent wake_up to {self.target_machine}")
            return True
            
        except Exception as e:
            logger.debug(f"[{machine_name}] Failed to send wake_up via socket: {e}")
            return False
    
    def _send_via_socket(self, payload: Dict[str, Any], job_id: str = None, machine_name: str = 'unknown') -> bool:
        """Send event via Unix socket. Returns True if successful."""
        try:
            socket_path = f'/tmp/statemachine-control-{self.target_machine}.sock'
            
            # Check if socket exists
            if not Path(socket_path).exists():
                logger.debug(f"[{machine_name}] Control socket not found: {socket_path}")
                return False
            
            # Create event message
            event_message = {
                'type': self.event_type,
                'payload': payload,
                'job_id': job_id
            }
            
            # Send via Unix socket (DGRAM)
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.sendto(json.dumps(event_message).encode('utf-8'), socket_path)
            sock.close()
            
            # Log sent message
            logger.info(f"[{machine_name}] 📤 Sent event {self.event_type} to {self.target_machine}")
            logger.debug(f"[{machine_name}] 📤 Event payload: {payload}")
            
            return True
            
        except Exception as e:
            logger.debug(f"[{machine_name}] Failed to send via socket: {e}")
            return False
    
    def _process_payload(self, template: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process payload template with context substitution"""
        if not template:
            return {}

        # Support forwarding entire payload as template string
        # If template is a string like "{event_data.payload}", return the dict directly
        if isinstance(template, str):
            if template == '{event_data.payload}':
                event_data = context.get('event_data', {})
                return event_data.get('payload', {}) if event_data else {}
            # Could expand to other {context.var} whole-dict forwards in future
            logger.warning(
                f"[{context.get('machine_name', 'unknown')}] "
                f"Payload template is string '{template}' but not '{event_data.payload}'. "
                f"Treating as empty payload."
            )
            return {}

        processed = {}
        current_job = context.get('current_job', {})
        job_data = current_job.get('data', {}) if current_job else {}
        event_data = context.get('event_data', {})
        event_payload = event_data.get('payload', {}) if event_data else {}

        # DEBUG: Comprehensive logging of context state
        logger.info(f"[SendEvent._process_payload] === CONTEXT DEBUG START ===")
        logger.info(f"[SendEvent._process_payload] Template: {template}")
        logger.info(f"[SendEvent._process_payload] event_data exists: {'event_data' in context}")
        logger.info(f"[SendEvent._process_payload] event_data: {event_data}")
        logger.info(f"[SendEvent._process_payload] event_payload type: {type(event_payload)}")
        logger.info(f"[SendEvent._process_payload] event_payload: {event_payload}")
        logger.info(f"[SendEvent._process_payload] === CONTEXT DEBUG END ===")

        # Support both context formats: current_job.id and direct context.id
        job_id = current_job.get('id') if current_job else context.get('id')

        # Also get source_job_id from current_job directly (database field)
        source_job_id = current_job.get('source_job_id') if current_job else None

        # Get job_id from event payload if available (for relaying)
        event_job_id = event_payload.get('job_id')

        for key, value in template.items():
            if isinstance(value, str):
                # Handle event_data.payload.* substitution (with nested field support)
                if value.startswith('{event_data.payload.') and value.endswith('}'):
                    payload_path = value[20:-1]  # Remove '{event_data.payload.' and '}'
                    
                    # Support nested access via dot notation (e.g., user.id, result.image_path)
                    extracted_value = event_payload
                    path_parts = payload_path.split('.')
                    
                    for part in path_parts:
                        if isinstance(extracted_value, dict) and part in extracted_value:
                            extracted_value = extracted_value[part]
                        else:
                            machine_name = context.get('machine_name', 'unknown')
                            logger.warning(
                                f"[{machine_name}] Nested payload path '{payload_path}' not found "
                                f"(failed at '{part}'), using None"
                            )
                            extracted_value = None
                            break
                    
                    # Recursively substitute placeholders in extracted value
                    if isinstance(extracted_value, str) and '{id}' in extracted_value:
                        # Use event job_id if available, otherwise current job_id
                        substitute_id = event_job_id or job_id
                        extracted_value = extracted_value.replace('{id}', substitute_id if substitute_id else '{id}')
                    
                    processed[key] = extracted_value
                # Simple string substitution
                elif value == '{id}':
                    processed[key] = job_id
                elif value == '{job_id}':
                    processed[key] = job_id
                elif value == '{face_job_id}':
                    processed[key] = f"face_{job_id}" if job_id else value
                elif value == '{source_job_id}':
                    # Try multiple sources for source_job_id
                    processed[key] = source_job_id or job_data.get('source_job_id')
                elif value == '{final_image}':
                    processed[key] = f"6-final/{job_id}-final.png" if job_id else value
                # Generic context variable substitution (e.g., {last_error}, {current_state})
                elif value.startswith('{') and value.endswith('}'):
                    var_name = value[1:-1]  # Remove { and }
                    if var_name in context:
                        processed[key] = context[var_name]
                    else:
                        machine_name = context.get('machine_name', 'unknown')
                        logger.warning(f"[{machine_name}] Context variable '{var_name}' not found, using placeholder")
                        processed[key] = value
                else:
                    # Handle any string that contains {id} placeholder
                    if '{id}' in value:
                        processed[key] = value.replace('{id}', job_id if job_id else '{id}')
                    else:
                        processed[key] = value
            else:
                processed[key] = value

        return processed