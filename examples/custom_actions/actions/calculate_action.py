"""
Custom Calculate Action - Demonstrates custom action with computation
"""

from statemachine_engine.actions.base import BaseAction


class CalculateAction(BaseAction):
    """
    Custom action that performs a calculation.
    
    YAML Usage:
        actions:
          - type: calculate
            params:
              operation: add  # add, subtract, multiply, divide
              success: calculated
    """
    
    async def execute(self, context):
        """Execute calculation action"""
        # Get numbers from event payload
        payload = context.get('event_data', {}).get('payload', {})
        a = payload.get('a', 0)
        b = payload.get('b', 0)
        
        # Get operation from config or payload
        operation = self.config.get('params', {}).get('operation', payload.get('operation', 'add'))
        
        # Perform calculation
        if operation == 'add':
            result = a + b
            symbol = '+'
        elif operation == 'subtract':
            result = a - b
            symbol = '-'
        elif operation == 'multiply':
            result = a * b
            symbol = '*'
        elif operation == 'divide':
            result = a / b if b != 0 else 'undefined'
            symbol = '/'
        else:
            result = 'unknown operation'
            symbol = '?'
        
        # Log result
        self.logger.info(f"Calculation: {a} {symbol} {b} = {result}")
        
        # Store result in context for next actions
        context['calculation_result'] = result
        
        # Return success event
        return self.config.get('params', {}).get('success', 'success')
