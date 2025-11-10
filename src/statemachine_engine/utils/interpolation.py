"""
Shared variable interpolation utility for state machine engine.

This module provides generic variable substitution functionality that can be
used across the engine and all actions. It supports:

- Simple variables: {job_id}, {id}, {status}
- Nested keys with dot notation: {event_data.payload.job_id}
- Recursive interpolation of complex structures (dicts, lists)
- Preservation of unknown placeholders
- Type safety (non-string values pass through unchanged)

Extracted from engine.py to eliminate code duplication across:
- Engine._substitute_variables() / _interpolate_config()
- CompleteJobAction._interpolate_variables()
- StartFSMAction._interpolate_variables()
- SendEventAction (inline usage)

Usage:
    from statemachine_engine.utils.interpolation import interpolate_value, interpolate_config
    
    # Single string interpolation
    result = interpolate_value("Job {job_id}", {"job_id": "123"})
    # Returns: "Job 123"
    
    # Recursive config interpolation
    config = {"cmd": "{job_id}", "nested": {"path": "{output}"}}
    result = interpolate_config(config, {"job_id": "123", "output": "/tmp"})
    # Returns: {"cmd": "123", "nested": {"path": "/tmp"}}
"""
import re
from typing import Any, Dict, List, Optional, Union


def interpolate_value(template: Any, context: Optional[Dict[str, Any]]) -> Any:
    """
    Interpolate variables in a single value (typically a string).
    
    Replaces {variable} placeholders with values from context. Supports:
    - Simple variables: {job_id}
    - Nested paths: {event_data.payload.job_id}
    - Unknown placeholders are preserved as-is
    - Type preservation: If template is ONLY a placeholder, returns original type
    
    Args:
        template: Value to interpolate. If not a string, returned unchanged.
        context: Dictionary containing variable values. Can be None.
    
    Returns:
        Interpolated value. Non-strings and None values returned unchanged.
        When template is a single placeholder, preserves the original value type.
    
    Examples:
        >>> interpolate_value("Job {job_id}", {"job_id": "123"})
        "Job 123"
        
        >>> interpolate_value("{count}", {"count": 42})
        42  # Type preserved when template is only a placeholder
        
        >>> interpolate_value("Count: {count}", {"count": 42})
        "Count: 42"  # String when mixed with text
        
        >>> interpolate_value("{items}", {"items": [1, 2, 3]})
        [1, 2, 3]  # Type preserved
    """
    if not isinstance(template, str):
        return template
    
    if context is None:
        context = {}
    
    # Pattern matches {variable_name} or {nested.path.name}
    # Variable names must start with letter or underscore, can contain alphanumeric and underscore
    pattern = r'\{([a-zA-Z_][a-zA-Z0-9_.]*)\}'
    
    # Special case: If template is EXACTLY a single placeholder, preserve original type
    single_match = re.fullmatch(pattern, template)
    if single_match:
        key = single_match.group(1)
        
        # Handle nested keys with dot notation
        if '.' in key:
            parts = key.split('.')
            obj = context
            
            for part in parts:
                if isinstance(obj, dict):
                    obj = obj.get(part)
                    if obj is None:
                        # Path not found - return original placeholder string
                        return template
                else:
                    # Intermediate value is not a dict - return placeholder
                    return template
            
            # Successfully traversed entire path - return original type
            return obj if obj is not None else template
        
        # Handle simple keys - return original type
        value = context.get(key)
        if value is not None:
            return value
        
        # Key not found - return placeholder
        return template
    
    # Multiple placeholders or mixed text - convert to strings
    def replace_match(match):
        key = match.group(1)
        
        # Handle nested keys with dot notation (e.g., event_data.payload.job_id)
        if '.' in key:
            parts = key.split('.')
            obj = context
            
            for part in parts:
                if isinstance(obj, dict):
                    obj = obj.get(part)
                    if obj is None:
                        # Path not found - keep original placeholder
                        return match.group(0)
                else:
                    # Intermediate value is not a dict - keep placeholder
                    return match.group(0)
            
            # Successfully traversed entire path
            return str(obj) if obj is not None else match.group(0)
        
        # Handle simple keys (e.g., job_id)
        value = context.get(key)
        if value is not None:
            return str(value)
        
        # Key not found - keep placeholder
        return match.group(0)
    
    return re.sub(pattern, replace_match, template)


def interpolate_config(
    config: Union[Dict[str, Any], List[Any], Any],
    context: Optional[Dict[str, Any]]
) -> Union[Dict[str, Any], List[Any], Any]:
    """
    Recursively interpolate variables in a configuration structure.
    
    Traverses dictionaries and lists, interpolating string values while
    preserving non-string types (int, bool, float, None) unchanged.
    
    Args:
        config: Configuration to interpolate. Can be dict, list, or primitive.
        context: Dictionary containing variable values. Can be None.
    
    Returns:
        New structure with interpolated values. Original config is not modified.
    
    Examples:
        >>> config = {
        ...     "cmd": "{job_id}",
        ...     "params": {"user": "{user}"},
        ...     "timeout": 30
        ... }
        >>> interpolate_config(config, {"job_id": "123", "user": "alice"})
        {"cmd": "123", "params": {"user": "alice"}, "timeout": 30}
    """
    if context is None:
        context = {}
    
    # Handle None explicitly
    if config is None:
        return None
    
    # Handle dictionaries recursively
    if isinstance(config, dict):
        interpolated = {}
        for key, value in config.items():
            if isinstance(value, str):
                # Interpolate string values
                interpolated[key] = interpolate_value(value, context)
            elif isinstance(value, dict):
                # Recursively process nested dicts
                interpolated[key] = interpolate_config(value, context)
            elif isinstance(value, list):
                # Recursively process lists
                interpolated[key] = interpolate_config(value, context)
            else:
                # Pass through other types unchanged (int, bool, float, None, etc.)
                interpolated[key] = value
        return interpolated
    
    # Handle lists recursively
    if isinstance(config, list):
        interpolated = []
        for item in config:
            if isinstance(item, str):
                # Interpolate string values
                interpolated.append(interpolate_value(item, context))
            elif isinstance(item, (dict, list)):
                # Recursively process nested structures
                interpolated.append(interpolate_config(item, context))
            else:
                # Pass through other types unchanged
                interpolated.append(item)
        return interpolated
    
    # For all other types (int, bool, float, None, objects, etc.)
    # Pass through unchanged
    return config
