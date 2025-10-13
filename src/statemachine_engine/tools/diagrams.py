#!/usr/bin/env python3
"""FSM Diagram Generator - Core Logic

Generates Mermaid stateDiagram-v2 from YAML configs with composite states.

MAIN FUNCTIONS:
- generate_mermaid_diagram()      - Main flow with composites
- generate_error_handling_diagram() - Error flow view
- generate_stop_handling_diagram()  - Stop/shutdown flow
- generate_main_overview()         - High-level composite boundaries
- generate_composite_subdiagram()  - Detailed composite internals
- generate_markdown()              - Complete Markdown docs
- generate_diagram_files()         - Modern format (.mermaid + metadata.json)

COMPOSITE STATE LOGIC:
  State Groups: Parsed from YAML comments (# === GROUP NAME ===)
  Internal: from_state.group == to_state.group (inside composite)
  External: from_state.group != to_state.group (between composites)
  Entry States: Transitions from outside -> inside group
  Exit States: Transitions from inside -> outside group

TRANSITION CLASSIFICATION:
  1. Build state -> group reverse mapping
  2. For each transition, lookup groups
  3. Same group = internal, different = external, from='*' = special

MERMAID SYNTAX:
    stateDiagram-v2
        [*] --> StateA
        state Composite {
            [*] --> InternalState
            InternalState --> OtherState : event
            OtherState --> [*]
        }
        StateA --> Composite
        Composite --> [*]

  Name sanitization: Replace hyphens/spaces with underscores

OUTPUT FORMATS:
  Legacy: Single .md with embedded Mermaid (main, error, stop flows + tables)
  Modern: Separate files - main.mermaid, {Composite}.mermaid, metadata.json

METADATA STRUCTURE:
    {"machine_name": "name",
     "diagrams": {
       "main": {"file": "main.mermaid", "composites": [...]},
       "Composite": {"file": "Composite.mermaid", "states": [...],
                     "entry_states": [...], "exit_states": [...], "parent": "main"}
     }}

HELPERS:
  get_composite_for_state(), get_internal/external/exit_transitions(),
  generate_states_table(), generate_events_table()

USAGE:
    config = load_yaml('config/machine.yaml')
    markdown = generate_markdown(config, 'config/machine.yaml')
    generate_diagram_files(config, 'config/machine.yaml', 'docs/fsm-diagrams')
"""

import yaml
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
import argparse


def load_yaml(file_path: str) -> Dict[str, Any]:
    """Load YAML configuration file."""
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML file {file_path}: {e}")
        sys.exit(1)


def generate_error_handling_diagram(config: Dict[str, Any]) -> str:
    """Generate Mermaid diagram focused on error handling flows."""
    
    states = config.get('states', [])
    transitions = config.get('transitions', [])
    
    # Find error-related transitions and states
    error_transitions = []
    error_states = set()
    
    for transition in transitions:
        event = transition.get('event', '')
        from_state = transition.get('from', '')
        to_state = transition.get('to', '')
        
        # Error-related events and states
        if 'error' in event.lower() or to_state == 'error_cleanup':
            error_transitions.append(transition)
            error_states.add(from_state)
            error_states.add(to_state)
    
    # Add error_cleanup related transitions
    for transition in transitions:
        from_state = transition.get('from', '')
        to_state = transition.get('to', '')
        
        if from_state == 'error_cleanup' or to_state == 'error_cleanup':
            error_transitions.append(transition)
            error_states.add(from_state)
            error_states.add(to_state)
    
    if not error_transitions:
        return ""
    
    mermaid = ["```mermaid", "stateDiagram-v2"]
    mermaid.append("    %% Error Handling Flow")
    
    # Add relevant states
    for state in error_states:
        if state == '*':
            continue
        clean_state = state.replace('-', '_').replace(' ', '_')
        if state == 'error_cleanup':
            mermaid.append(f"    {clean_state} : 🚨 {state}")
        else:
            mermaid.append(f"    {clean_state} : {state}")
    
    # Add error transitions
    for transition in error_transitions:
        from_state = transition.get('from', '')
        to_state = transition.get('to', '')
        event = transition.get('event', '')
        
        if from_state == '*':
            # Show representative states for wildcard
            for state in ['waiting', 'processing', 'generating']:
                if state in [s for s in states if isinstance(s, str)]:
                    clean_from = state.replace('-', '_').replace(' ', '_')
                    clean_to = to_state.replace('-', '_').replace(' ', '_')
                    clean_event = event.replace('-', '_').replace(' ', '_')
                    mermaid.append(f"    {clean_from} --> {clean_to} : {clean_event}")
                    break
        else:
            clean_from = from_state.replace('-', '_').replace(' ', '_')
            clean_to = to_state.replace('-', '_').replace(' ', '_')
            clean_event = event.replace('-', '_').replace(' ', '_')
            mermaid.append(f"    {clean_from} --> {clean_to} : {clean_event}")
    
    mermaid.append("```")
    return '\n'.join(mermaid)


def generate_stop_handling_diagram(config: Dict[str, Any]) -> str:
    """Generate Mermaid diagram focused on stop/shutdown flows."""
    
    states = config.get('states', [])
    transitions = config.get('transitions', [])
    
    # Find stop-related transitions and states
    stop_transitions = []
    stop_states = set()
    
    for transition in transitions:
        event = transition.get('event', '')
        from_state = transition.get('from', '')
        to_state = transition.get('to', '')
        
        # Stop-related events and states
        if event == 'stop' or to_state == 'stopped':
            stop_transitions.append(transition)
            stop_states.add(from_state)
            stop_states.add(to_state)
    
    if not stop_transitions:
        return ""
    
    mermaid = ["```mermaid", "stateDiagram-v2"]
    mermaid.append("    %% Stop/Shutdown Flow")
    
    # Add relevant states
    for state in stop_states:
        if state == '*':
            continue
        clean_state = state.replace('-', '_').replace(' ', '_')
        if state == 'stopped':
            mermaid.append(f"    {clean_state} : ⏹️ {state}")
        else:
            mermaid.append(f"    {clean_state} : {state}")
    
    # Add terminal state
    mermaid.append("    stopped --> [*]")
    
    # Add stop transitions
    for transition in stop_transitions:
        from_state = transition.get('from', '')
        to_state = transition.get('to', '')
        event = transition.get('event', '')
        
        if from_state == '*':
            # Show representative states for wildcard
            active_states = [s for s in states if isinstance(s, str) and s not in ['stopped', 'error_cleanup']]
            for state in active_states[:3]:  # Show first 3 active states
                clean_from = state.replace('-', '_').replace(' ', '_')
                clean_to = to_state.replace('-', '_').replace(' ', '_')
                clean_event = event.replace('-', '_').replace(' ', '_')
                mermaid.append(f"    {clean_from} --> {clean_to} : {clean_event}")
        else:
            clean_from = from_state.replace('-', '_').replace(' ', '_')
            clean_to = to_state.replace('-', '_').replace(' ', '_')
            clean_event = event.replace('-', '_').replace(' ', '_')
            mermaid.append(f"    {clean_from} --> {clean_to} : {clean_event}")
    
    mermaid.append("```")
    return '\n'.join(mermaid)


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


def generate_mermaid_diagram(config: Dict[str, Any], yaml_path: str = None) -> str:
    """Generate Mermaid state diagram from FSM configuration with composite states."""
    
    # Extract basic info
    initial_state = config.get('initial_state', 'unknown')
    states = config.get('states', [])
    transitions = config.get('transitions', [])
    
    # Parse state groups from YAML comments
    state_groups = {}
    if yaml_path:
        state_groups = parse_state_groups(yaml_path)
    
    # Create reverse mapping: state -> group
    state_to_group = {}
    for group_name, group_states in state_groups.items():
        for state in group_states:
            state_to_group[state] = group_name
    
    # Start building the diagram
    mermaid = ["```mermaid", "stateDiagram-v2"]
    
    # Add initial state
    if initial_state != 'unknown':
        mermaid.append(f"    [*] --> {initial_state}")
        mermaid.append("")
    
    # Separate transitions into internal (within groups) and external (between groups)
    internal_transitions_by_group = {}
    external_transitions = []
    
    for transition in transitions:
        from_state = transition.get('from', '')
        to_state = transition.get('to', '')
        event = transition.get('event', '')
        
        # Skip wildcard, error and stop transitions for main diagram
        if from_state == '*' or event in ['error', 'stop']:
            continue
        
        from_group = state_to_group.get(from_state)
        to_group = state_to_group.get(to_state)
        
        # If both states are in the same group, it's internal
        if from_group and from_group == to_group:
            if from_group not in internal_transitions_by_group:
                internal_transitions_by_group[from_group] = []
            internal_transitions_by_group[from_group].append(transition)
        else:
            external_transitions.append(transition)
    
    # Generate composite states for each group
    for group_name, group_states in state_groups.items():
        # Create composite for every group (even if no internal transitions)
        
        composite_name = group_name.replace(' ', '').replace('STATES', '').strip()
        mermaid.append(f"    %% {group_name}")
        mermaid.append(f"    state {composite_name} {{")
        
        # Find entry points (states that are targets from outside the group)
        entry_states = set()
        for t in transitions:
            if t.get('to') in group_states and state_to_group.get(t.get('from')) != group_name:
                entry_states.add(t.get('to'))
        
        # Add entry points
        if entry_states:
            for entry in sorted(entry_states):
                clean_entry = entry.replace('-', '_').replace(' ', '_')
                mermaid.append(f"        [*] --> {clean_entry}")
        
        # Add internal transitions for this group (if any)
        if group_name in internal_transitions_by_group:
            for transition in internal_transitions_by_group[group_name]:
                from_state = transition.get('from', '')
                to_state = transition.get('to', '')
                event = transition.get('event', '')
                
                clean_from = from_state.replace('-', '_').replace(' ', '_')
                clean_to = to_state.replace('-', '_').replace(' ', '_')
                clean_event = event.replace('-', '_').replace(' ', '_')
                mermaid.append(f"        {clean_from} --> {clean_to} : {clean_event}")
        
        # Find exit transitions (from this group to outside)
        exit_transitions = [t for t in transitions 
                           if t.get('from') in group_states 
                           and state_to_group.get(t.get('to')) != group_name
                           and t.get('event') not in ['error', 'stop']]
        
        if exit_transitions:
            for t in exit_transitions:
                clean_from = t.get('from').replace('-', '_').replace(' ', '_')
                clean_event = t.get('event').replace('-', '_').replace(' ', '_')
                mermaid.append(f"        {clean_from} --> [*] : {clean_event}")
        
        mermaid.append("    }")
        mermaid.append("")
    
    # Add external transitions (between composites or to/from non-composite states)
    if external_transitions:
        mermaid.append("    %% Transitions")
        for transition in external_transitions:
            from_state = transition.get('from', '')
            to_state = transition.get('to', '')
            event = transition.get('event', '')
            
            from_group = state_to_group.get(from_state)
            to_group = state_to_group.get(to_state)
            
            # Use group name if state belongs to a composite, otherwise use state name
            if from_group and from_group in state_groups:
                clean_from = from_group.replace(' ', '').replace('STATES', '').strip()
            else:
                clean_from = from_state.replace('-', '_').replace(' ', '_')
            
            if to_group and to_group in state_groups:
                clean_to = to_group.replace(' ', '').replace('STATES', '').strip()
            else:
                clean_to = to_state.replace('-', '_').replace(' ', '_')
            
            clean_event = event.replace('-', '_').replace(' ', '_')
            mermaid.append(f"    {clean_from} --> {clean_to} : {clean_event}")
        mermaid.append("")
    
    # Add terminal states
    terminal_states = ['stopped', 'error_cleanup']
    for state in states:
        if isinstance(state, str) and state in terminal_states:
            clean_state = state.replace('-', '_').replace(' ', '_')
            mermaid.append(f"    {clean_state} --> [*]")
    
    mermaid.append("```")
    return '\n'.join(mermaid)


def generate_states_table(config: Dict[str, Any]) -> str:
    """Generate table of states with their actions."""
    states = config.get('states', [])
    actions = config.get('actions', {})
    
    if not states or not actions:
        return ""
    
    table = ["## States Overview", "", "| State | Description | Key Actions |", "|-------|-------------|-------------|"]
    
    for state in states:
        if isinstance(state, str):
            state_actions = actions.get(state, [])
            
            # Extract description from first log action or state name
            description = state.replace('_', ' ').replace('-', ' ').title()
            key_actions = []
            
            for action in state_actions:
                if isinstance(action, dict):
                    action_type = action.get('type', '')
                    action_desc = action.get('description', '')
                    
                    if action_type == 'log' and action_desc:
                        description = action_desc.strip('📡🎨🔄✅🔀👤🔍🔗⏳😴💤🧹⚠️⏹️')
                        break
            
            # Get key action types
            for action in state_actions[:3]:  # Show first 3 actions
                if isinstance(action, dict):
                    action_type = action.get('type', '')
                    if action_type:
                        key_actions.append(action_type)
            
            actions_str = ', '.join(key_actions) if key_actions else 'N/A'
            table.append(f"| `{state}` | {description} | {actions_str} |")
    
    return '\n'.join(table)


def generate_events_table(config: Dict[str, Any]) -> str:
    """Generate table of events."""
    events = config.get('events', [])
    
    if not events:
        return ""
    
    table = ["## Events Overview", "", "| Event | Type | Description |", "|-------|------|-------------|"]
    
    for event in events:
        if isinstance(event, str):
            # Categorize events
            event_type = "Internal"
            if event.endswith('_done') or event.endswith('_completed'):
                event_type = "Success"
            elif event.endswith('_failed') or event == 'error':
                event_type = "Error"
            elif event in ['start', 'stop', 'wake_up']:
                event_type = "Control"
            elif 'job' in event:
                event_type = "Job"
            
            description = event.replace('_', ' ').replace('-', ' ').title()
            table.append(f"| `{event}` | {event_type} | {description} |")
    
    return '\n'.join(table)


def generate_markdown(config: Dict[str, Any], yaml_path: str) -> str:
    """Generate complete Markdown documentation."""
    
    name = config.get('name', 'State Machine')
    description = config.get('description', '')
    metadata = config.get('metadata', {})
    
    # Header
    md_content = [
        f"# {name}",
        "",
        f"**Description:** {description}",
        "",
        f"**Generated from:** `{os.path.basename(yaml_path)}`",
        f"**Machine Name:** `{metadata.get('machine_name', 'unknown')}`",
        f"**Version:** `{metadata.get('version', 'unknown')}`",
        f"**Job Type:** `{metadata.get('job_type', 'unknown')}`",
        "",
        "---",
        "",
    ]
    
    # State Machine Diagram
    md_content.extend([
        "## Main State Machine Flow",
        "",
        generate_mermaid_diagram(config, yaml_path),
        "",
        "---",
        ""
    ])
    
    # Error Handling Diagram
    error_diagram = generate_error_handling_diagram(config)
    if error_diagram:
        md_content.extend([
            "## Error Handling Flow",
            "",
            error_diagram,
            "",
            "---",
            ""
        ])
    
    # Stop Handling Diagram
    stop_diagram = generate_stop_handling_diagram(config)
    if stop_diagram:
        md_content.extend([
            "## Stop/Shutdown Flow",
            "",
            stop_diagram,
            "",
            "---",
            ""
        ])
    
    # States Table
    states_table = generate_states_table(config)
    if states_table:
        md_content.extend([states_table, "", "---", ""])
    
    # Events Table
    events_table = generate_events_table(config)
    if events_table:
        md_content.extend([events_table, "", "---", ""])
    
    # Configuration Summary
    states = config.get('states', [])
    events = config.get('events', [])
    transitions = config.get('transitions', [])
    
    md_content.extend([
        "## Configuration Summary",
        "",
        f"- **States:** {len(states)}",
        f"- **Events:** {len(events)}",
        f"- **Transitions:** {len(transitions)}",
        f"- **Initial State:** `{config.get('initial_state', 'unknown')}`",
        "",
        "---",
        "",
        f"*Generated by yaml_to_fsm.py*"
    ])
    
    return '\n'.join(md_content)


def get_composite_for_state(state: str, state_groups: Dict[str, List[str]]) -> str:
    """Find which composite state contains a given state."""
    for group_name, group_states in state_groups.items():
        if state in group_states:
            return group_name.replace(' ', '').replace('STATES', '').strip()
    return None


def get_internal_transitions(config: Dict[str, Any], group_states: List[str]) -> List[Dict[str, Any]]:
    """Get transitions that are internal to a group of states."""
    transitions = config.get('transitions', [])
    internal = []
    
    for transition in transitions:
        from_state = transition.get('from', '')
        to_state = transition.get('to', '')
        event = transition.get('event', '')
        
        # Skip wildcard and special events
        if from_state == '*' or event in ['error', 'stop']:
            continue
            
        if from_state in group_states and to_state in group_states:
            internal.append(transition)
    
    return internal


def get_external_transitions(config: Dict[str, Any], state_groups: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """Get transitions between different composite states."""
    transitions = config.get('transitions', [])
    external = []
    
    # Create reverse mapping
    state_to_group = {}
    for group_name, group_states in state_groups.items():
        for state in group_states:
            state_to_group[state] = group_name
    
    for transition in transitions:
        from_state = transition.get('from', '')
        to_state = transition.get('to', '')
        event = transition.get('event', '')
        
        # Skip wildcard and special events
        if from_state == '*' or event in ['error', 'stop']:
            continue
        
        from_group = state_to_group.get(from_state)
        to_group = state_to_group.get(to_state)
        
        # External if states are in different groups (or one is not in any group)
        if from_group != to_group:
            external.append(transition)
    
    return external


def get_exit_transitions(config: Dict[str, Any], group_states: List[str], all_groups: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """Get transitions that exit from a group to other groups."""
    transitions = config.get('transitions', [])
    exits = []
    
    for transition in transitions:
        from_state = transition.get('from', '')
        to_state = transition.get('to', '')
        event = transition.get('event', '')
        
        # Skip wildcard and special events
        if from_state == '*' or event in ['error', 'stop']:
            continue
        
        if from_state in group_states and to_state not in group_states:
            exits.append(transition)
    
    return exits


def generate_main_overview(config: Dict[str, Any], state_groups: Dict[str, List[str]]) -> str:
    """Generate top-level diagram showing only composite state boundaries."""
    lines = ["stateDiagram-v2"]
    
    # Add initial state - connect to composite containing initial state
    initial_state = config.get('initial_state', 'unknown')
    if initial_state != 'unknown':
        initial_composite = get_composite_for_state(initial_state, state_groups)
        if initial_composite:
            lines.append(f"    [*] --> {initial_composite}")
        else:
            # Fallback: if initial state is not in any composite, connect directly
            lines.append(f"    [*] --> {initial_state}")
        lines.append("")
    
    # Show each composite as a simple state (NO NOTES - they cause syntax errors)
    for group_name, group_states in state_groups.items():
        composite_name = group_name.replace(' ', '').replace('STATES', '').strip()
        lines.append(f"    %% {group_name} ({len(group_states)} states)")
        lines.append(f"    state {composite_name}")
        lines.append("")
    
    # Only show transitions BETWEEN composite states
    external_transitions = get_external_transitions(config, state_groups)
    
    # Group external transitions by composite pairs
    composite_transitions = {}
    for transition in external_transitions:
        from_composite = get_composite_for_state(transition['from'], state_groups)
        to_composite = get_composite_for_state(transition['to'], state_groups)
        
        if from_composite and to_composite and from_composite != to_composite:
            key = (from_composite, to_composite)
            if key not in composite_transitions:
                composite_transitions[key] = []
            composite_transitions[key].append(transition.get('event', ''))
    
    if composite_transitions:
        lines.append("    %% Transitions between composites")
        for (from_comp, to_comp), events in composite_transitions.items():
            # Show first event as label
            event_label = events[0] if events else ''
            lines.append(f"    {from_comp} --> {to_comp} : {event_label}")
        lines.append("")
    
    # Add terminal states - connect their composites to [*]
    terminal_states = ['stopped', 'error_cleanup']
    states = config.get('states', [])
    terminal_composites = set()
    for state in states:
        if isinstance(state, str) and state in terminal_states:
            terminal_composite = get_composite_for_state(state, state_groups)
            if terminal_composite:
                terminal_composites.add(terminal_composite)
            else:
                # Fallback: if terminal state is not in any composite, connect directly
                clean_state = state.replace('-', '_').replace(' ', '_')
                lines.append(f"    {clean_state} --> [*]")
    
    # Add composite --> [*] connections for terminal states
    for composite in terminal_composites:
        lines.append(f"    {composite} --> [*]")
    
    return '\n'.join(lines)


def generate_composite_subdiagram(
    config: Dict[str, Any],
    group_name: str,
    group_states: List[str],
    all_groups: Dict[str, List[str]]
) -> str:
    """Generate detailed diagram for ONE composite state."""
    composite_name = group_name.replace(' ', '').replace('STATES', '').strip()
    lines = ["stateDiagram-v2"]
    lines.append(f"    %% Detailed view of {composite_name}")
    lines.append("")
    
    # Find entry points
    transitions = config.get('transitions', [])
    entry_states = set()
    for t in transitions:
        if t.get('to') in group_states and t.get('from') not in group_states:
            entry_states.add(t.get('to'))
    
    # Add entry points
    if entry_states:
        for entry in sorted(entry_states):
            clean_entry = entry.replace('-', '_').replace(' ', '_')
            lines.append(f"    [*] --> {clean_entry}")
    else:
        # No external entry points - this might be the initial composite
        # Check if this composite contains the initial state
        initial_state = config.get('initial_state')
        if initial_state and initial_state in group_states:
            # This is the initial composite - add [*] to initial state
            clean_initial = initial_state.replace('-', '_').replace(' ', '_')
            lines.append(f"    [*] --> {clean_initial}")
        elif group_states:
            # Fallback: add [*] to first state in group to avoid Mermaid errors
            first_state = sorted(group_states)[0]
            clean_first = first_state.replace('-', '_').replace(' ', '_')
            lines.append(f"    [*] --> {clean_first}")
    
    lines.append("")
    
    # Show full internal transitions
    lines.append(f"    %% Internal transitions")
    internal_transitions = get_internal_transitions(config, group_states)
    for transition in internal_transitions:
        from_state = transition.get('from', '')
        to_state = transition.get('to', '')
        event = transition.get('event', '')
        
        clean_from = from_state.replace('-', '_').replace(' ', '_')
        clean_to = to_state.replace('-', '_').replace(' ', '_')
        clean_event = event.replace('-', '_').replace(' ', '_')
        lines.append(f"    {clean_from} --> {clean_to} : {clean_event}")
    
    lines.append("")
    
    # Show other composites as simple states (NO NOTES - they cause syntax errors)
    lines.append(f"    %% External composites")
    for other_group_name in all_groups.keys():
        if other_group_name != group_name:
            other_composite = other_group_name.replace(' ', '').replace('STATES', '').strip()
            lines.append(f"    state {other_composite}")
    
    lines.append("")
    
    # Show transitions TO external composites
    lines.append(f"    %% Transitions to other composites")
    exit_transitions = get_exit_transitions(config, group_states, all_groups)
    for transition in exit_transitions:
        from_state = transition['from']
        to_state = transition['to']
        event = transition.get('event', '')
        
        to_composite = get_composite_for_state(to_state, all_groups)
        
        clean_from = from_state.replace('-', '_').replace(' ', '_')
        clean_event = event.replace('-', '_').replace(' ', '_')
        
        if to_composite:
            lines.append(f"    {clean_from} --> {to_composite} : {clean_event}")
        else:
            # Target is not in any composite
            clean_to = to_state.replace('-', '_').replace(' ', '_')
            lines.append(f"    {clean_from} --> {clean_to} : {clean_event}")
    
    return '\n'.join(lines)


def generate_metadata(
    config: Dict[str, Any],
    state_groups: Dict[str, List[str]],
    composite_files: Dict[str, str]
) -> Dict[str, Any]:
    """Generate metadata.json with diagram relationships."""
    machine_name = config.get('metadata', {}).get('machine_name', config.get('name', 'unknown'))
    transitions = config.get('transitions', [])
    
    metadata = {
        "machine_name": machine_name,
        "diagrams": {
            "main": {
                "file": "main.mermaid",
                "title": f"{config.get('name', 'State Machine')} Overview",
                "description": "High-level state machine flow with composite states",
                "composites": [
                    group_name.replace(' ', '').replace('STATES', '').strip()
                    for group_name in state_groups.keys()
                ]
            }
        }
    }
    
    # Add metadata for each composite
    for group_name, group_states in state_groups.items():
        composite_name = group_name.replace(' ', '').replace('STATES', '').strip()
        
        # Find entry and exit states
        entry_states = []
        exit_states = []
        
        for t in transitions:
            if t.get('to') in group_states and t.get('from') not in group_states:
                if t.get('to') not in entry_states:
                    entry_states.append(t.get('to'))
            if t.get('from') in group_states and t.get('to') not in group_states:
                if t.get('from') not in exit_states:
                    exit_states.append(t.get('from'))
        
        metadata["diagrams"][composite_name] = {
            "file": composite_files[group_name],
            "title": group_name.replace('STATES', '').strip(),
            "description": f"Detailed view of {group_name.lower()}",
            "states": group_states,
            "entry_states": entry_states,
            "exit_states": exit_states,
            "parent": "main"
        }
    
    return metadata


def generate_diagram_files(config: Dict[str, Any], yaml_path: str, output_dir: str = "docs/fsm-diagrams"):
    """
    Generate separate Mermaid files for main diagram and each composite state.
    
    Structure:
    - docs/fsm-diagrams/{machine_name}/main.mermaid
    - docs/fsm-diagrams/{machine_name}/{COMPOSITE}.mermaid
    - docs/fsm-diagrams/{machine_name}/metadata.json
    """
    machine_name = config.get('metadata', {}).get('machine_name', config.get('name', 'unknown'))
    machine_dir = os.path.join(output_dir, machine_name)
    os.makedirs(machine_dir, exist_ok=True)
    
    # Parse state groups
    state_groups = parse_state_groups(yaml_path)
    
    if not state_groups:
        print(f"⚠️  No state groups found in {yaml_path}. Skipping new format generation.")
        return
    
    # Generate main overview diagram
    print(f"  Generating main.mermaid...")
    main_diagram = generate_main_overview(config, state_groups)
    with open(os.path.join(machine_dir, 'main.mermaid'), 'w') as f:
        f.write(main_diagram)
    
    # Generate composite-specific subdiagrams
    composite_files = {}
    for group_name, group_states in state_groups.items():
        composite_name = group_name.replace(' ', '').replace('STATES', '').strip()
        filename = f"{composite_name}.mermaid"
        
        print(f"  Generating {filename}...")
        subdiagram = generate_composite_subdiagram(config, group_name, group_states, state_groups)
        filepath = os.path.join(machine_dir, filename)
        with open(filepath, 'w') as f:
            f.write(subdiagram)
        
        composite_files[group_name] = filename
    
    # Generate metadata.json
    print(f"  Generating metadata.json...")
    metadata = generate_metadata(config, state_groups, composite_files)
    with open(os.path.join(machine_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Generated new format in {machine_dir}/")
    print(f"   - 1 main diagram")
    print(f"   - {len(composite_files)} composite subdiagrams")
    print(f"   - 1 metadata file")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Generate FSM diagrams from YAML configuration')
    parser.add_argument('yaml_file', help='Path to YAML configuration file')
    parser.add_argument('output_file', nargs='?', help='Output Markdown file (optional, for backward compatibility)')
    parser.add_argument('--output-dir', default='docs/fsm-diagrams', help='Output directory for new format (default: docs/fsm-diagrams)')
    parser.add_argument('--old-format-only', action='store_true', help='Generate only old Markdown format')
    parser.add_argument('--new-format-only', action='store_true', help='Generate only new .mermaid format')
    
    args = parser.parse_args()
    yaml_path = args.yaml_file
    
    # Load configuration
    config = load_yaml(yaml_path)
    
    # Generate old format (Markdown with embedded Mermaid)
    if not args.new_format_only:
        if args.output_file:
            output_path = args.output_file
        else:
            # Use machine_name from metadata, fallback to filename
            machine_name = config.get('metadata', {}).get('machine_name')
            if not machine_name:
                # Fallback to YAML filename
                machine_name = Path(yaml_path).stem
            # Place markdown within fsm-diagrams folder
            output_path = f"{args.output_dir}/{machine_name}/{machine_name}_fsm.md"
        
        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate and write Markdown
        markdown = generate_markdown(config, yaml_path)
        try:
            with open(output_path, 'w') as f:
                f.write(markdown)
            print(f"✅ Generated Markdown: {output_path}")
        except Exception as e:
            print(f"Error writing output file {output_path}: {e}")
            sys.exit(1)
    
    # Generate new format (separate .mermaid files + metadata.json)
    if not args.old_format_only:
        print(f"\n📁 Generating new format in {args.output_dir}/...")
        generate_diagram_files(config, yaml_path, args.output_dir)
        print("")


if __name__ == "__main__":
    main()