"""
AddToListAction - Add item to a list in context

Helper action for managing lists in context. Useful for tracking spawned
jobs, collecting results, or building data across multiple action executions.

YAML Usage:
    actions:
      spawning_worker:
        - type: add_to_list
          list_key: "spawned_jobs"
          value: "{current_job.id}"
          success: tracked
"""
import logging
from typing import Dict, Any

from ..base import BaseAction
from ...utils.interpolation import interpolate_value

logger = logging.getLogger(__name__)


class AddToListAction(BaseAction):
    """
    Add an item to a list in context.
    
    Creates the list if it doesn't exist, otherwise appends to existing list.
    Supports variable interpolation in the value.
    
    Config:
        list_key: Context key for the list (default: "items")
        value: Value to append (supports variable interpolation)
        success: Event to emit on success (default: "success")
    
    YAML Usage:
        actions:
          tracking:
            - type: add_to_list
              list_key: "spawned_jobs"
              value: "{current_job.id}"
              success: job_tracked
            
            - type: add_to_list
              list_key: "results"
              value: "{output_path}"
    
    Context Updates:
        context[list_key]: List with new item appended
    
    Returns:
        - success event: Item added successfully
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.list_key = config.get('list_key', 'items')
        self.value_template = config.get('value')
    
    async def execute(self, context: Dict[str, Any]) -> str:
        """Add item to list in context"""
        machine_name = context.get('machine_name', 'unknown')
        
        # Validate configuration
        if self.value_template is None:
            logger.error(f"[{machine_name}] AddToListAction: 'value' is required")
            return 'error'
        
        # Interpolate value from context
        value = interpolate_value(self.value_template, context)
        
        # Check if interpolation failed (still contains placeholders)
        if isinstance(value, str) and '{' in value and '}' in value:
            logger.warning(
                f"[{machine_name}] AddToListAction: value contains unresolved variables: {value}"
            )
            # Continue anyway - might be intentional
        
        # Create list if doesn't exist
        if self.list_key not in context:
            context[self.list_key] = []
            logger.debug(f"[{machine_name}] Created new list in context['{self.list_key}']")
        
        # Verify it's actually a list
        if not isinstance(context[self.list_key], list):
            logger.error(
                f"[{machine_name}] AddToListAction: context['{self.list_key}'] is not a list "
                f"(type: {type(context[self.list_key]).__name__})"
            )
            return 'error'
        
        # Append value to list
        context[self.list_key].append(value)
        
        logger.info(
            f"[{machine_name}] Added '{value}' to {self.list_key} "
            f"(list now has {len(context[self.list_key])} items)"
        )
        
        return self.config.get('success', 'success')
