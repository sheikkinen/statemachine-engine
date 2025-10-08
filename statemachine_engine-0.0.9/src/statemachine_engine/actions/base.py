"""
BaseAction - Abstract base class for pluggable state machine actions

IMPORTANT: Changes via Change Management, see CLAUDE.md

Defines the standard interface for all state machine actions loaded dynamically from YAML configuration. 
Actions receive config parameters from YAML and execution context from the state machine, then return 
event names to trigger state transitions. Provides common functionality for configuration access, 
logging setup, and description handling across all action implementations.

KEY FILES:
- src/actions/bash_action.py - Shell command execution implementation  
- src/actions/check_queue_action.py - Job queue monitoring implementation
- src/state_machine/engine.py - Dynamic action loading and execution

KEY FUNCTIONS:
- execute(context) - Abstract method for action execution, returns event name
- get_description() - Get action description from config or generate default  
- get_config_value(key, default) - Retrieve configuration values with fallbacks
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseAction(ABC):
    """Base class for all state machine actions."""
    
    def __init__(self, action_config: Dict[str, Any]):
        """
        Initialize action with configuration.
        
        Args:
            action_config: Configuration dictionary from YAML
        """
        self.config = action_config
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> str:
        """
        Execute the action.
        
        Args:
            context: State machine context
            
        Returns:
            Event name to trigger next state transition
        """
        pass
    
    def get_description(self) -> str:
        """Get action description from config or default."""
        return self.config.get('description', f"{self.__class__.__name__} action")
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with optional default."""
        return self.config.get(key, default)
    
    def get_machine_name(self, context: Dict[str, Any]) -> str:
        """Get machine name from context for logging."""
        return context.get('machine_name', 'unknown')