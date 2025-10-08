"""
ActionLoader - Dynamic action class discovery and loading

IMPORTANT: Changes via Change Management, see CLAUDE.md

Provides automatic discovery and loading of action classes from the actions directory tree.
Supports nested action modules (e.g., actions/ideator/) without requiring hardcoded imports
in the state machine engine. Actions follow the naming convention: <action_type>_action.py
containing a class named <ActionType>Action inheriting from BaseAction.

KEY FEATURES:
- Auto-discovery of actions in actions/ and subdirectories
- Class name caching for performance
- Graceful ImportError handling with fallback
- Support for flat and nested action module structure

KEY FILES:
- src/actions/base.py - BaseAction interface definition
- src/state_machine/engine.py - Uses ActionLoader for dynamic action execution
- src/actions/ideator/*.py - Example of nested action modules

KEY FUNCTIONS:
- load_action_class(action_type) - Load action class by type name
- _discover_action_modules() - Find all *_action.py files
- _build_class_name(action_type) - Convert action_type to ClassName
"""

import logging
import importlib
from pathlib import Path
from typing import Dict, Type, Optional

logger = logging.getLogger(__name__)


class ActionLoader:
    """
    Dynamically load action classes from actions directory tree.
    
    Supports both flat structure (actions/bash_action.py) and nested structure
    (actions/ideator/generate_concepts_action.py).
    """
    
    def __init__(self, actions_root: str = None):
        """
        Initialize action loader.
        
        Args:
            actions_root: Root directory for actions (default: auto-detect from this file)
        """
        if actions_root is None:
            # Auto-detect: src/actions relative to this file
            this_file = Path(__file__)
            actions_root = str(this_file.parent.parent / 'actions')
        
        self.actions_root = Path(actions_root)
        self._action_map: Dict[str, str] = {}  # action_type -> module_path
        self._class_cache: Dict[str, Type] = {}  # action_type -> loaded class
        
        # Action type aliases (for backward compatibility)
        self._aliases: Dict[str, str] = {
            'activity_log': 'log',  # activity_log maps to log_action.py
        }
        
        self._discover_action_modules()
    
    def _discover_action_modules(self) -> None:
        """
        Discover all action modules in the actions directory tree.
        
        Searches for *_action.py files and maps action_type to module path.
        """
        if not self.actions_root.exists():
            logger.warning(f"Actions root not found: {self.actions_root}")
            return
        
        # Find all *_action.py files recursively
        for action_file in self.actions_root.rglob('*_action.py'):
            # Skip __pycache__ and other non-module files
            if '__pycache__' in str(action_file):
                continue
            
            # Get relative path from actions root
            rel_path = action_file.relative_to(self.actions_root.parent)

            # Convert path to module notation: actions/builtin/bash_action.py
            # -> statemachine_engine.actions.builtin.bash_action
            module_path = 'statemachine_engine.' + str(rel_path.with_suffix('')).replace('/', '.')
            
            # Extract action type from filename: generate_concepts_action.py -> generate_concepts
            action_type = action_file.stem.replace('_action', '')
            
            self._action_map[action_type] = module_path
            # Removed per-action logging - too verbose
        
        # Single INFO log summarizing discovery
        logger.info(f"Action loader initialized: {len(self._action_map)} actions available")
    
    def _build_class_name(self, action_type: str) -> str:
        """
        Build action class name from action type.
        
        Converts snake_case action_type to PascalCase class name.
        Example: generate_concepts -> GenerateConceptsAction
        
        Args:
            action_type: Action type (e.g., 'generate_concepts')
            
        Returns:
            Class name (e.g., 'GenerateConceptsAction')
        """
        words = action_type.split('_')
        pascal_case = ''.join(word.capitalize() for word in words)
        return f"{pascal_case}Action"
    
    def load_action_class(self, action_type: str) -> Optional[Type]:
        """
        Load action class by action type.
        
        First checks cache, then tries to import from discovered modules.
        If action not found in discovery, attempts generic fallback loading.
        
        Args:
            action_type: Action type (e.g., 'bash', 'generate_concepts')
            
        Returns:
            Action class or None if not found
        """
        # Check for aliases first
        resolved_action_type = self._aliases.get(action_type, action_type)
        
        # Check cache
        if resolved_action_type in self._class_cache:
            return self._class_cache[resolved_action_type]
        
        # Check if action was discovered
        if resolved_action_type not in self._action_map:
            logger.warning(f"Action type '{action_type}' not discovered. Available: {list(self._action_map.keys())}")
            return None
        
        module_path = self._action_map[resolved_action_type]
        class_name = self._build_class_name(resolved_action_type)
        
        try:
            # Import the module
            module = importlib.import_module(module_path)
            
            # Get the action class
            action_class = getattr(module, class_name)
            
            # Cache for future use (cache both original and resolved)
            self._class_cache[resolved_action_type] = action_class
            if action_type != resolved_action_type:
                self._class_cache[action_type] = action_class
            
            # Only log first load of each action type (not every use)
            if len(self._class_cache) <= len(self._action_map):  # Still loading initial set
                logger.debug(f"Loaded: {action_type}")
            
            return action_class
            
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load action '{action_type}' from {module_path}.{class_name}: {e}")
            return None
    
    def get_available_actions(self) -> list:
        """Get list of all discovered action types."""
        return sorted(self._action_map.keys())
    
    def clear_cache(self) -> None:
        """Clear the class cache (useful for testing/reloading)."""
        self._class_cache.clear()
    
    def rediscover(self) -> None:
        """Re-scan the actions directory for new modules."""
        self._action_map.clear()
        self.clear_cache()
        self._discover_action_modules()


# Singleton instance for convenient access
_loader_instance: Optional[ActionLoader] = None


def get_action_loader() -> ActionLoader:
    """Get the singleton ActionLoader instance."""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = ActionLoader()
    return _loader_instance


def load_action_class(action_type: str) -> Optional[Type]:
    """
    Convenience function to load an action class.
    
    Args:
        action_type: Action type to load
        
    Returns:
        Action class or None if not found
    """
    loader = get_action_loader()
    return loader.load_action_class(action_type)
