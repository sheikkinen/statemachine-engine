"""
SetContextAction - Set a value in the context

Simple helper action to set or update context values. Useful for resetting
tracking lists, flags, or other state variables.

YAML Usage:
    actions:
      some_state:
        - type: set_context
          key: "my_variable"
          value: "some_value"
          success: value_set  # Optional event name
        
        - type: set_context
          key: "my_list"
          value: []  # Clear a list
        
        - type: set_context
          key: "counter"
          value: 0  # Reset a counter
"""
import logging
from typing import Dict, Any

from ..base import BaseAction

logger = logging.getLogger(__name__)


class SetContextAction(BaseAction):
    """
    Set a value in the context.
    
    Simple helper to set or update context variables. Supports any JSON-serializable
    value including strings, numbers, booleans, lists, and dictionaries.
    
    Config:
        key: Context key to set (required)
        value: Value to set (required) - can be any JSON-serializable type
        success: Event to return on success (default: "success")
    
    Context Updates:
        Sets context[key] = value
    
    Returns:
        - success event: Value set successfully
    
    Examples:
        # Clear a list
        - type: set_context
          key: "spawned_jobs"
          value: []
        
        # Set a flag
        - type: set_context
          key: "processing_enabled"
          value: true
        
        # Reset counter
        - type: set_context
          key: "retry_count"
          value: 0
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.key = config.get('key')
        self.value = config.get('value')
        
        if self.key is None:
            raise ValueError("SetContextAction requires 'key' parameter")
        if 'value' not in config:
            raise ValueError("SetContextAction requires 'value' parameter")
    
    async def execute(self, context: Dict[str, Any]) -> str:
        """Set the context value"""
        machine_name = context.get('machine_name', 'unknown')
        
        # Get old value for logging
        old_value = context.get(self.key, '<not set>')
        
        # Set the new value
        context[self.key] = self.value
        
        # Log the change
        logger.info(
            f"[{machine_name}] Set context['{self.key}'] = {self.value} "
            f"(was: {old_value})"
        )
        
        return self.config.get('success', 'success')
