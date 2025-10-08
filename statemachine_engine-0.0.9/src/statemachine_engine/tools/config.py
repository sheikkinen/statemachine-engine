"""FSM Configuration Loader

Loads YAML state machine configs and extracts state groups from comments.

FUNCTIONS:
- load_yaml(file_path) -> Dict: Load YAML with error handling (exits on error)
- parse_state_groups(yaml_path) -> Dict[str, List[str]]: Extract grouped states

STATE GROUP SYNTAX:
    states:
      # === INITIALIZATION STATES ===
      - waiting
      - checking_queue
      # === PROCESSING STATES ===
      - generating

  Format: # === GROUP NAME ===
  Groups consecutive states until next marker or section end.

ALGORITHM:
1. Parse line-by-line (preserves comments vs yaml.safe_load)
2. Detect "states:" section
3. Find group markers (# === ... ===)
4. Associate states ("- state") to current group
5. Exit on new top-level key

RETURNS: {"INITIALIZATION STATES": ["waiting", "checking_queue"], ...}

USAGE:
    config = load_yaml('config/machine.yaml')
    groups = parse_state_groups('config/machine.yaml')
"""

import yaml
import sys
from typing import Dict, List, Any


def load_yaml(file_path: str) -> Dict[str, Any]:
    """Load YAML configuration file."""
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML file {file_path}: {e}")
        sys.exit(1)


def parse_state_groups(yaml_path: str) -> Dict[str, List[str]]:
    """Parse state groups from YAML file comments."""
    state_groups = {}
    current_group = None
    
    try:
        with open(yaml_path, 'r') as f:
            in_states_section = False
            for line in f:
                line = line.rstrip()
                
                # Detect states section
                if line.strip().startswith('states:'):
                    in_states_section = True
                    continue
                
                # Exit states section when we hit a new top-level key
                if in_states_section and line and not line[0].isspace() and ':' in line:
                    break
                
                if in_states_section:
                    # Check for section comment
                    if '# ===' in line and '===' in line:
                        # Extract group name from comment
                        comment = line.split('#', 1)[1].strip()
                        group_name = comment.replace('===', '').strip().replace(' STATES', '')
                        current_group = group_name
                        state_groups[current_group] = []
                    # Check for state (starts with -)
                    elif line.strip().startswith('- ') and current_group:
                        state = line.strip()[2:].split('#')[0].strip()
                        if state:
                            state_groups[current_group].append(state)
    except Exception as e:
        print(f"Warning: Could not parse state groups: {e}")
    
    return state_groups
