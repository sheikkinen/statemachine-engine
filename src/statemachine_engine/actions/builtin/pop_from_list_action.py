"""
PopFromListAction - Pop first item from a list in context

Removes and returns the first item from a list stored in context. Useful for
iterating through a batch of items (like jobs) and processing them one by one.

YAML Usage:
    actions:
      processing_batch:
        - type: pop_from_list
          list_key: "pending_jobs"
          store_as: "current_job"
          success: has_job
          empty: batch_complete
        
        # Process the item...
        - type: do_something
          with: "{current_job}"
"""
import logging
from typing import Dict, Any

from ..base import BaseAction

logger = logging.getLogger(__name__)


class PopFromListAction(BaseAction):
    """
    Pop the first item from a list in context.
    
    Removes and returns the first item from a list. If the list is empty,
    returns an empty event. Useful for batch processing patterns where you
    want to iterate through a list of items.
    
    Config:
        list_key: Context key containing the list (default: "items")
        store_as: Context key to store the popped item (optional)
        success: Event to return when item popped (default: "item_popped")
        empty: Event to return when list is empty (default: "list_empty")
    
    Context Updates:
        - Updates context[list_key] with item removed
        - Sets context[store_as] = popped_item (if store_as provided)
    
    Returns:
        - success event: Item was popped from list
        - empty event: List was empty
    
    Examples:
        # Process batch of jobs
        - type: pop_from_list
          list_key: "pending_jobs"
          store_as: "current_job"
          success: has_job
          empty: all_jobs_processed
        
        # Iterate through items
        - type: pop_from_list
          list_key: "work_items"
          store_as: "item"
          success: continue_processing
          empty: done
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.list_key = config.get('list_key', 'items')
        self.store_as = config.get('store_as')
    
    async def execute(self, context: Dict[str, Any]) -> str:
        """Pop first item from list"""
        machine_name = context.get('machine_name', 'unknown')
        
        # Get the list from context
        items = context.get(self.list_key, [])
        
        # Check if list is a list type
        if not isinstance(items, list):
            logger.error(
                f"[{machine_name}] Context key '{self.list_key}' is not a list "
                f"(type: {type(items).__name__})"
            )
            return self.config.get('empty', 'list_empty')
        
        # Check if list is empty
        if not items:
            logger.info(
                f"[{machine_name}] List '{self.list_key}' is empty "
                f"(no more items to pop)"
            )
            return self.config.get('empty', 'list_empty')
        
        # Pop first item
        item = items.pop(0)
        
        # Update the list in context
        context[self.list_key] = items
        
        # Store the popped item if store_as is specified
        if self.store_as:
            context[self.store_as] = item
            logger.info(
                f"[{machine_name}] Popped item from '{self.list_key}' → "
                f"'{self.store_as}' ({len(items)} remaining)"
            )
        else:
            logger.info(
                f"[{machine_name}] Popped item from '{self.list_key}' "
                f"({len(items)} remaining)"
            )
        
        return self.config.get('success', 'item_popped')
