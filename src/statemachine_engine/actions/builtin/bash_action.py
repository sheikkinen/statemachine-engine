"""
BashAction - Execute shell commands with template parameter substitution and error mapping

IMPORTANT: Changes via Change Management, see CLAUDE.md

Executes bash commands defined in YAML configuration, substituting template parameters from job data
using {param_name} placeholders. Commands run with configurable timeout, and the action returns 
custom success events or mapped error events based on exit codes. Supports error mapping to specific 
events (e.g., exit code 1 → 'no_faces_detected') and prevents automatic job removal for recoverable 
errors that should be handled by state machine transitions.

KEY FILES:
- config/face_changer_database.yaml - YAML configuration with bash actions, error_mappings, and success events
- src/database/ - Database-backed job storage and management
- working/ - Temporary directory for safe file processing

KEY FUNCTIONS:
- execute(context) - Main action execution with parameter substitution, command running, and error mapping
- get_config_value() - Retrieve configuration values including error_mappings and success events

NEW FEATURES:
- error_mappings: Map exit codes to specific error events (e.g., "1": "no_faces_detected")
- success: Custom success event names instead of default 'job_done'
- Conditional job removal: Specific errors like 'no_faces_detected' bypass auto-removal
"""

import asyncio
import logging
from typing import Dict, Any
from ..base import BaseAction

logger = logging.getLogger(__name__)


class BashAction(BaseAction):
    """
    Action that executes bash commands with error mapping support.
    
    Returns:
    - Custom success event (from 'success' config) or 'job_done' on exit code 0
    - Mapped error event (from 'error_mappings' config) on specific exit codes  
    - Default 'error' event on unmapped failures
    
    Error Mapping Example:
    error_mappings:
      "1": "no_faces_detected"  # Exit code 1 → no_faces_detected event
      "2": "invalid_image"      # Exit code 2 → invalid_image event
    """
    
    async def execute(self, context: Dict[str, Any]) -> str:
        """
        Execute bash command and return event based on exit code.
        
        Args:
            context: State machine context containing current_job and queue
            
        Returns:
            - success event (config 'success' or 'job_done') on exit code 0
            - mapped error event (from 'error_mappings') on specific exit codes
            - 'error' on unmapped failures
            
        Error Handling:
            - Mapped errors (e.g., 'no_faces_detected') preserve job for state machine handling
            - Unmapped errors auto-remove job to prevent infinite retries
            - Timeouts and exceptions also auto-remove job
        """
        # Get command from job data first, fall back to config with parameter substitution
        job = context.get('current_job')
        command = None
        
        if job and isinstance(job.get('data'), dict):
            job_data = job['data']
            command = job_data.get('command')
        
        # Use config command and substitute parameters from job data (assumes add-job.sh usage)
        if not command:
            command = self.get_config_value('command')
            if command and job and isinstance(job.get('data'), dict):
                job_data = job['data']
                
                # Get context values for fallback substitution
                # Start with ALL context (includes id, last_error, etc.), then overlay job_data
                context_data = {**context}  # Start with full context (includes propagated job fields)
                
                # Overlay job_data (so job_data takes precedence over propagated context)
                context_data.update(job_data)
                
                # Add event payload data if available (for machine-to-machine communication)
                event_data = context.get('event_data', {})
                if event_data and isinstance(event_data, dict):
                    event_payload = event_data.get('payload', {})
                    if event_payload and isinstance(event_payload, dict):
                        # Merge event payload fields into context_data
                        for key, value in event_payload.items():
                            if key not in job_data:  # Don't override job data
                                context_data[key] = value
                
                # Handle fallback syntax first (e.g., {enhanced_prompt|pony_prompt})
                import re
                fallback_pattern = r'\{([^|}]+)\|([^}]+)\}'
                fallback_matches = re.findall(fallback_pattern, command)
                
                for primary_key, fallback_key in fallback_matches:
                    placeholder = f"{{{primary_key}|{fallback_key}}}"
                    quoted_placeholder = f"'{{{primary_key}|{fallback_key}}}'"

                    # Try primary key first, then fallback
                    value = context_data.get(primary_key)
                    if value is None:
                        value = context_data.get(fallback_key)

                    if value is not None:
                        # Handle quoted version - escape internal single quotes and wrap in single quotes
                        if quoted_placeholder in command:
                            # Escape single quotes in value for bash single-quote context
                            escaped_value = str(value).replace("'", "'\\''")
                            command = command.replace(quoted_placeholder, f"'{escaped_value}'")
                            machine_name = self.get_machine_name(context)
                            logger.debug(f"[{machine_name}] Substituted {quoted_placeholder} with '{escaped_value}' (using {primary_key if primary_key in context_data else fallback_key})")

                        # Handle unquoted version (separate from quoted, both can occur in same command)
                        if placeholder in command:
                            if isinstance(value, str) and ('/' in value or ' ' in value):
                                quoted_value = f'"{value}"'
                            else:
                                quoted_value = str(value)
                            command = command.replace(placeholder, quoted_value)
                            machine_name = self.get_machine_name(context)
                            logger.debug(f"[{machine_name}] Substituted {placeholder} with {quoted_value} (using {primary_key if primary_key in context_data else fallback_key})")
                
                # Substitute regular parameters using {param_name} placeholders
                for key, value in context_data.items():
                    if key != 'event':  # Skip event field
                        placeholder = f"{{{key}}}"
                        quoted_placeholder = f"'{{{key}}}'"

                        # First handle quoted placeholders - escape internal single quotes and wrap in single quotes
                        if quoted_placeholder in command:
                            # Escape single quotes in value for bash single-quote context
                            escaped_value = str(value).replace("'", "'\\''")
                            command = command.replace(quoted_placeholder, f"'{escaped_value}'")
                            machine_name = self.get_machine_name(context)
                            logger.debug(f"[{machine_name}] Substituted {quoted_placeholder} with '{escaped_value}'")

                        # Then handle unquoted placeholders (separate from quoted, both can occur in same command)
                        if placeholder in command:
                            # For unquoted placeholders, add quotes for paths/strings with spaces
                            if isinstance(value, str) and ('/' in value or ' ' in value):
                                quoted_value = f'"{value}"'
                            else:
                                quoted_value = str(value)
                            command = command.replace(placeholder, quoted_value)
                            machine_name = self.get_machine_name(context)
                            logger.debug(f"[{machine_name}] Substituted {placeholder} with {quoted_value}")
                
                # Check for any remaining unsubstituted placeholders
                remaining_placeholders = re.findall(r'\{[^}]+\}', command)
                if remaining_placeholders:
                    machine_name = self.get_machine_name(context)
                    logger.warning(f"[{machine_name}] Unsubstituted placeholders found: {remaining_placeholders}")
            
        if not command:
            machine_name = self.get_machine_name(context)
            logger.error(f"[{machine_name}] No command specified in job data or bash action config")
            return 'error'
        
        timeout = self.get_config_value('timeout', 30)
        job_id = job['id'] if job else 'unknown'
        
        # Use description for user-facing messages (INFO level), command details only at DEBUG
        description = self.get_config_value('description')
        machine_name = self.get_machine_name(context)
        if description:
            # User-facing descriptions logged at INFO (but skip repetitive/routine ones)
            # Suppress: Initialize, Check, Reset (cleanup), mkdir operations
            skip_prefixes = ['🔄 Initialize', '📋 Check', '🔄 Reset']
            if not any(description.startswith(prefix) for prefix in skip_prefixes):
                logger.info(f"[{machine_name}] {description[:60]}")
        
        # Command details only at DEBUG level (but skip simple mkdir commands)
        # Add rate limiting for frequently executed commands
        if not hasattr(self.__class__, '_cmd_count'):
            self.__class__._cmd_count = {}
        
        cmd_key = command[:50]  # Use first 50 chars as key
        if cmd_key not in self.__class__._cmd_count:
            self.__class__._cmd_count[cmd_key] = 0
        self.__class__._cmd_count[cmd_key] += 1
        
        if not command.startswith('mkdir -p'):
            # Log first occurrence and every 100th to track frequency
            if self.__class__._cmd_count[cmd_key] == 1:
                logger.info(f"[{machine_name}] [BASH FREQUENCY TRACKER] First execution: {command}")
            elif self.__class__._cmd_count[cmd_key] % 100 == 0:
                logger.warning(f"[{machine_name}] [BASH FREQUENCY TRACKER] Command executed {self.__class__._cmd_count[cmd_key]} times: {command}")
            
            logger.debug(f"[{machine_name}] Executing command for job {job_id}: {command}")
        
        try:
            # Execute command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Kill the process if it's still running
                if process.returncode is None:
                    process.kill()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        # Force kill if graceful kill failed
                        process.terminate()
                raise  # Re-raise to be caught by outer handler
            
            # Only log output if non-empty and meaningful (skip routine messages)
            stdout_text = stdout.decode().strip() if stdout else ""
            stderr_text = stderr.decode().strip() if stderr else ""
            
            routine_messages = [
                "No stuck processing jobs found",
                "Successfully",
                "Job created:",
            ]
            
            is_routine = any(msg in stdout_text for msg in routine_messages)
            
            if stdout_text and not is_routine:
                logger.debug(f"[{machine_name}] Output: {stdout_text[:200]}")  # Truncate long output
            if stderr_text:
                logger.warning(f"[{machine_name}] Error output: {stderr_text[:200]}")
            
            # Check exit code (don't log success for every command)
            if process.returncode == 0:
                # Include command context in completion log
                cmd_summary = command[:50] + "..." if len(command) > 50 else command
                logger.debug(f"[{machine_name}] Command completed (exit 0): {cmd_summary}")
                
                # Don't auto-complete jobs here - let the state machine handle job completion
                # when the entire pipeline is done
                
                # Don't clear current job here - it may be needed by subsequent actions in the same state
                
                # Return custom success event if specified, otherwise 'job_done'
                success_event = self.get_config_value('success', 'job_done')
                return success_event
            else:
                error_output = stderr.decode().strip() if stderr else "No error output"
                logger.error(f"[{machine_name}] Command failed with exit code {process.returncode} for job {job_id}")
                logger.error(f"[{machine_name}] Failed command: {command}")
                logger.error(f"[{machine_name}] Error output: {error_output}")

                # Store error details in context for error_cleanup state with improved formatting
                # Include command on separate line for better readability in logs
                context['last_error'] = f"Command failed (exit {process.returncode}): {error_output}\nCommand: {command}"
                context['last_error_action'] = 'bash'
                context['last_error_command'] = command
                context['last_error_exit_code'] = process.returncode

                # Check for error mapping based on exit code
                error_mappings = self.get_config_value('error_mappings', {})
                if str(process.returncode) in error_mappings:
                    mapped_error = error_mappings[str(process.returncode)]
                    logger.info(f"[{machine_name}] Mapping exit code {process.returncode} to event: {mapped_error}")
                    
                    # For specific error types like no_faces_detected, don't auto-remove job
                    # Let the state machine handle it through proper transitions
                    if mapped_error in ['no_faces_detected']:
                        return mapped_error
                
                # For unmapped errors, let the state machine handle job failure via error event
                # Don't auto-remove jobs here - the state machine will handle proper cleanup
                # and status updates via error_cleanup state
                
                # Clear current job on error to prevent infinite loops
                context.pop('current_job', None)
                
                # Return mapped error event if available, otherwise default 'error'
                return error_mappings.get(str(process.returncode), 'error')
                
        except asyncio.TimeoutError:
            machine_name = self.get_machine_name(context)
            timeout_msg = f"Command timed out after {timeout} seconds"
            logger.error(f"[{machine_name}] {timeout_msg} for job {job_id}")
            logger.error(f"[{machine_name}] Timed out command: {command}")

            # Store timeout error in context with improved formatting
            context['last_error'] = f"{timeout_msg}\nCommand: {command}"
            context['last_error_action'] = 'bash'
            context['last_error_command'] = command
            
            # Let the state machine handle job failure via error event
            # Don't auto-remove jobs here - the state machine will handle proper cleanup
            # and status updates via error_cleanup state
            
            # Clear current job on timeout to prevent infinite loops
            context.pop('current_job', None)
            return 'error'
            
        except Exception as e:
            machine_name = self.get_machine_name(context)
            error_msg = f"Command execution exception: {str(e)}"
            logger.error(f"[{machine_name}] {error_msg} for job {job_id}")
            logger.error(f"[{machine_name}] Failed command: {command}")

            # Store exception details in context with improved formatting
            context['last_error'] = f"{error_msg}\nCommand: {command}"
            context['last_error_action'] = 'bash'
            context['last_error_command'] = command

            # Let the state machine handle job failure via error event
            # Don't auto-remove jobs here - the state machine will handle proper cleanup
            # and status updates via error_cleanup state

            # Clear current job on exception to prevent infinite loops
            context.pop('current_job', None)
            return 'error'