"""
StartFsmAction - Spawn new FSM instances as separate processes

This action spawns a new state machine instance as a separate process,
enabling concurrent execution of multiple FSM instances managed by a
controller FSM.
"""
import logging
import subprocess
import re
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from ..base import BaseAction

logger = logging.getLogger(__name__)


class StartFsmAction(BaseAction):
    """
    Action to spawn a new FSM instance with optional context passing.
    
    This enables a controller FSM to dynamically spawn worker FSMs with
    job-specific context, implementing patterns like queue-based task
    processing with concurrent workers.
    
    YAML Usage:
        actions:
          - type: start_fsm
            yaml_path: "config/worker.yaml"
            machine_name: "worker_{job_id}"
            context_vars:
              - current_job.id as job_id    # Extract nested, rename
              - report_id                    # Pass flat variable
              - report_title                 # Pass flat variable
            success: worker_started
            error: spawn_failed
            store_pid: true
            additional_args:
              - "--debug"
              - "--log-level=INFO"
    
    Context Variables:
        Supports three syntaxes:
        1. Flat: "variable_name" - Copy as-is from context
        2. Nested: "parent.child.field" - Extract using dot notation
        3. Renamed: "source as target" - Extract and rename
        
        Missing variables are logged as warnings but don't fail the spawn.
        Context is passed to spawned FSM via --initial-context JSON argument.
    
    Example with variable interpolation:
        # Controller reads job from queue
        actions:
          - type: start_fsm
            yaml_path: "config/{job_type}_worker.yaml"
            machine_name: "worker_{job_type}_{job_id}"
            context_vars:
              - current_job.id as job_id
              - current_job.type as job_type  
              - input_path
              - output_path
            success: worker_spawned
            
        # Context variables like {job_id} are replaced in strings
        # Context vars are extracted and passed to spawned worker
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.yaml_path = config.get('yaml_path')
        self.machine_name = config.get('machine_name')
        self.store_pid = config.get('store_pid', False)
        self.additional_args = config.get('additional_args', [])
        self.context_vars = config.get('context_vars', [])

    async def execute(self, context: Dict[str, Any]) -> str:
        """
        Spawn a new FSM instance as a subprocess.
        
        Args:
            context: Execution context with variables for interpolation
            
        Returns:
            Event name: 'success' (default) or custom success/error event
        """
        try:
            # Validate required parameters
            if not self.yaml_path:
                logger.error("StartFsmAction: yaml_path is required")
                return self.get_config_value('error', 'error')
            
            if not self.machine_name:
                logger.error("StartFsmAction: machine_name is required")
                return self.get_config_value('error', 'error')
            
            # Interpolate variables in yaml_path and machine_name
            yaml_path = self._interpolate_variables(self.yaml_path, context)
            machine_name = self._interpolate_variables(self.machine_name, context)
            
            # Build command
            command = [
                'statemachine',
                yaml_path,
                '--machine-name',
                machine_name
            ]
            
            # Extract and pass context variables if specified
            if self.context_vars:
                context_data = self._extract_context_vars(context)
                
                if context_data:
                    try:
                        # Serialize to JSON
                        context_json = json.dumps(context_data, separators=(',', ':'))
                        
                        # Warn if context is large
                        if len(context_json) > 4096:
                            logger.warning(f"StartFsmAction: Context JSON is large ({len(context_json)} bytes)")
                        
                        # Add to command
                        command.extend(['--initial-context', context_json])
                        
                    except (TypeError, ValueError) as e:
                        logger.error(f"StartFsmAction: Failed to serialize context: {e}")
                        return self.get_config_value('error', 'error')
            
            # Add additional arguments if specified
            if self.additional_args:
                command.extend(self.additional_args)
            
            logger.info(f"StartFsmAction: Spawning FSM with command: {' '.join(command)}")
            
            # Spawn process (non-blocking, detached)
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # Detach from parent process group
            )
            
            pid = process.pid
            logger.info(f"StartFsmAction: Spawned FSM '{machine_name}' with PID {pid}")
            
            # Optionally store PID in context for tracking
            if self.store_pid:
                if 'spawned_pids' not in context:
                    context['spawned_pids'] = []
                context['spawned_pids'].append(pid)
                logger.debug(f"StartFsmAction: Stored PID {pid} in context")
            
            # Return success event
            return self.get_config_value('success', 'success')
            
        except FileNotFoundError as e:
            logger.error(f"StartFsmAction: Command not found - {e}")
            return self.get_config_value('error', 'error')
        except Exception as e:
            logger.error(f"StartFsmAction: Failed to spawn FSM - {e}")
            return self.get_config_value('error', 'error')
    
    def _extract_context_vars(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract specified variables from context.
        
        Supports three syntaxes:
        1. Simple: "variable_name" - Copy as-is
        2. Nested: "parent.child.field" - Extract using dot notation
        3. Renamed: "source as target" - Extract and rename
        
        Args:
            context: Source context dictionary
            
        Returns:
            Dictionary with extracted variables
        """
        extracted = {}
        
        for var_spec in self.context_vars:
            # Parse "source as target" or just "source"
            if ' as ' in var_spec:
                source, target = var_spec.split(' as ', 1)
                source = source.strip()
                target = target.strip()
            else:
                source = target = var_spec.strip()
            
            # Extract value (supports dot notation)
            value = self._get_nested_value(context, source)
            
            if value is not None:
                extracted[target] = value
            else:
                logger.warning(f"StartFsmAction: Context variable '{source}' not found, skipping")
        
        return extracted
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Optional[Any]:
        """
        Get value from nested dict using dot notation.
        
        Args:
            data: Source dictionary
            path: Dot-separated path (e.g., "current_job.id")
            
        Returns:
            Value at path, or None if not found
        """
        keys = path.split('.')
        value = data
        
        try:
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return value
        except (KeyError, TypeError):
            return None
    
    def _interpolate_variables(self, template: str, context: Dict[str, Any]) -> str:
        """
        Replace {variable} placeholders with values from context.
        
        Supports simple and nested variable substitution:
        - {job_id} -> context['job_id']
        - {current_job.id} -> context['current_job']['id']
        - {job_type} -> context['job_type']
        - {machine_name} -> context['machine_name']
        
        Args:
            template: String with {variable} placeholders
            context: Dictionary with variable values
            
        Returns:
            String with variables replaced
        """
        result = template
        
        # Find all {variable} and {nested.variable} patterns
        pattern = r'\{([\w\.]+)\}'
        matches = re.findall(pattern, template)
        
        # Replace each variable
        for var_path in matches:
            # Handle nested paths like current_job.id
            if '.' in var_path:
                parts = var_path.split('.')
                value = context
                try:
                    for part in parts:
                        value = value[part]
                    result = result.replace(f'{{{var_path}}}', str(value))
                except (KeyError, TypeError):
                    logger.warning(f"StartFsmAction: Nested variable '{var_path}' not found in context")
            # Handle simple variables
            else:
                if var_path in context:
                    value = context[var_path]
                    result = result.replace(f'{{{var_path}}}', str(value))
                else:
                    logger.warning(f"StartFsmAction: Variable '{var_path}' not found in context")
        
        return result
