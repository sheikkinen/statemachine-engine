"""
Custom Greet Action - Demonstrates custom action implementation
"""

from statemachine_engine.actions.base import BaseAction


class GreetAction(BaseAction):
    """
    Custom action that greets a user.
    
    YAML Usage:
        actions:
          - type: greet
            params:
              success: greeted
    """
    
    async def execute(self, context):
        """Execute greeting action"""
        # Get name from event payload
        payload = context.get('event_data', {}).get('payload', {})
        name = payload.get('name', 'World')
        
        # Log greeting
        self.logger.info(f"Hello, {name}! 👋")
        
        # Return success event
        return self.config.get('params', {}).get('success', 'success')
