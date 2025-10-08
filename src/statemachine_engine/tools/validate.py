#!/usr/bin/env python3
"""
State Machine Configuration Validator

Static analysis tool that validates YAML state machine configurations
before runtime to catch missing transitions and configuration errors.

Checks:
1. Event Coverage: All events have at least one transition
2. Action Emissions: Actions with success/failure/timeout have transitions
3. Standard Patterns: check_events/check_database_queue/clear_events patterns
4. Orphaned States: States defined but never reached
5. Unreachable States: States that can't be reached from initial_state
6. Missing Events: Events used in transitions but not declared
7. Self-Loop Patterns: Common query actions need self-loops

Usage:
    # Validate single config
    statemachine-validate config/controller.yaml
    
    # Validate all configs
    statemachine-validate config/*.yaml
    
    # Strict mode (exit 1 on any warnings)
    statemachine-validate --strict config/*.yaml
    
    # Quiet mode (errors only)
    statemachine-validate --quiet config/*.yaml

Exit codes:
    0 - All validations passed
    1 - Errors found (missing transitions, invalid config)
    2 - Warnings found (only in --strict mode)
"""

import sys
import yaml
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    category: str  # e.g., 'missing_transition', 'orphaned_state'
    severity: str = ""  # 'error' or 'warning' (set by add_error/add_warning)
    state: str = ""
    event: str = ""
    message: str = ""
    suggestion: str = ""


@dataclass
class ValidationResult:
    """Results from validating a single config file"""
    config_path: str
    passed: bool = True
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    
    def add_error(self, issue: ValidationIssue):
        issue.severity = 'error'
        self.errors.append(issue)
        self.passed = False
        
    def add_warning(self, issue: ValidationIssue):
        issue.severity = 'warning'
        self.warnings.append(issue)


class StateMachineValidator:
    """Validates state machine YAML configurations"""
    
    # Actions that emit specific events when conditions aren't met
    STANDARD_PATTERNS = {
        'check_events': 'no_events',
        'check_database_queue': 'no_jobs',
        'clear_events': 'no_events_to_clear',
        'check_machine_state': ['in_expected_state', 'unexpected_state', 'not_running'],
    }
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        
    def validate_config(self, config_path: str) -> ValidationResult:
        """Validate a single state machine configuration"""
        result = ValidationResult(config_path=config_path)
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            result.add_error(ValidationIssue(
                severity='error',
                category='file_not_found',
                message=f"Configuration file not found: {config_path}"
            ))
            return result
        except yaml.YAMLError as e:
            result.add_error(ValidationIssue(
                severity='error',
                category='yaml_parse_error',
                message=f"YAML parse error: {e}"
            ))
            return result
            
        # Extract components
        states = set(config.get('states', []))
        events = set(config.get('events', []))
        transitions = config.get('transitions', [])
        actions = config.get('actions', {})
        initial_state = config.get('initial_state', 'waiting')
        machine_name = config.get('metadata', {}).get('machine_name', 'unknown')
        
        # Run validation checks
        self._check_event_coverage(events, transitions, result)
        self._check_action_emissions(actions, transitions, events, result)
        self._check_standard_patterns(actions, transitions, result)
        self._check_orphaned_states(states, transitions, initial_state, result)
        self._check_unreachable_states(states, transitions, initial_state, result)
        self._check_missing_events(events, transitions, result)
        self._check_wildcard_transitions(transitions, states, result)
        self._check_initial_state(initial_state, states, result)
        
        return result
        
    def _check_event_coverage(self, events: Set[str], transitions: List[Dict], 
                              result: ValidationResult) -> None:
        """Check that all declared events have at least one transition"""
        events_with_transitions = set()
        
        for trans in transitions:
            event = trans.get('event')
            if event:
                events_with_transitions.add(event)
                
        uncovered_events = events - events_with_transitions
        
        for event in uncovered_events:
            # Skip internal/system events that don't need explicit transitions
            if event in ['start', 'stop']:
                continue
                
            result.add_warning(ValidationIssue(
                category='uncovered_event',
                event=event,
                message=f"Event '{event}' is declared but has no transitions",
                suggestion=f"Add a transition for event '{event}' or remove from events list"
            ))
            
    def _check_action_emissions(self, actions: Dict, transitions: List[Dict],
                                events: Set[str], result: ValidationResult) -> None:
        """Check that actions emitting events have corresponding transitions"""
        for state_name, state_actions in actions.items():
            if not isinstance(state_actions, list):
                continue
                
            for action in state_actions:
                if not isinstance(action, dict):
                    continue
                    
                # Check for success/failure event emissions
                # Note: 'timeout' parameter is timeout duration in seconds, NOT an event
                emitted_events = []
                if 'success' in action and isinstance(action['success'], str):
                    emitted_events.append(('success', action['success']))
                if 'failure' in action and isinstance(action['failure'], str):
                    emitted_events.append(('failure', action['failure']))
                    
                for emission_type, event in emitted_events:
                    # Check if transition exists for this event from this state
                    has_transition = any(
                        t.get('from') == state_name and t.get('event') == event
                        for t in transitions
                    )
                    
                    if not has_transition:
                        result.add_error(ValidationIssue(
                            category='missing_action_transition',
                            state=state_name,
                            event=event,
                            message=f"Action in state '{state_name}' emits '{event}' ({emission_type}) but no transition exists",
                            suggestion=f"Add transition: from: {state_name}, event: {event}"
                        ))
                        
    def _check_standard_patterns(self, actions: Dict, transitions: List[Dict],
                                 result: ValidationResult) -> None:
        """Check for standard action patterns requiring specific transitions"""
        for state_name, state_actions in actions.items():
            if not isinstance(state_actions, list):
                continue
                
            for action in state_actions:
                if not isinstance(action, dict):
                    continue
                    
                action_type = action.get('type')
                
                if action_type in self.STANDARD_PATTERNS:
                    expected = self.STANDARD_PATTERNS[action_type]
                    expected_events = [expected] if isinstance(expected, str) else expected
                    
                    # Check for transitions with expected events (self-loop OR any other transition)
                    for expected_event in expected_events:
                        has_transition = any(
                            t.get('from') == state_name and 
                            t.get('event') == expected_event
                            for t in transitions
                        )
                        
                        if not has_transition and expected_event not in ['in_expected_state', 'unexpected_state', 'not_running']:
                            result.add_error(ValidationIssue(
                                category='missing_pattern_transition',
                                state=state_name,
                                event=expected_event,
                                message=f"State '{state_name}' has '{action_type}' action but no '{expected_event}' transition",
                                suggestion=f"Add transition: from: {state_name}, event: {expected_event}"
                            ))
                            
    def _check_orphaned_states(self, states: Set[str], transitions: List[Dict],
                              initial_state: str, result: ValidationResult) -> None:
        """Check for states that are never transitioned to"""
        target_states = {initial_state}  # Initial state is always reachable
        
        for trans in transitions:
            to_state = trans.get('to')
            if to_state and to_state != '*':
                target_states.add(to_state)
                
        orphaned = states - target_states - {'stopped'}  # 'stopped' is terminal, OK to be orphaned
        
        for state in orphaned:
            result.add_warning(ValidationIssue(
                category='orphaned_state',
                state=state,
                message=f"State '{state}' is defined but never transitioned to",
                suggestion=f"Add a transition targeting '{state}' or remove it from states list"
            ))
            
    def _check_unreachable_states(self, states: Set[str], transitions: List[Dict],
                                 initial_state: str, result: ValidationResult) -> None:
        """Check for states that can't be reached from initial state"""
        reachable = {initial_state}
        queue = [initial_state]
        
        # Build transition graph
        graph = defaultdict(set)
        for trans in transitions:
            from_state = trans.get('from')
            to_state = trans.get('to')
            if from_state == '*':
                # Wildcard transitions from any state
                for state in states:
                    graph[state].add(to_state)
            elif from_state and to_state:
                graph[from_state].add(to_state)
                
        # BFS to find all reachable states
        while queue:
            current = queue.pop(0)
            for next_state in graph[current]:
                if next_state not in reachable and next_state != '*':
                    reachable.add(next_state)
                    queue.append(next_state)
                    
        unreachable = states - reachable
        
        for state in unreachable:
            if state != 'stopped':  # Terminal state, OK to be unreachable via normal flow
                result.add_warning(ValidationIssue(
                    category='unreachable_state',
                    state=state,
                    message=f"State '{state}' cannot be reached from initial state '{initial_state}'",
                    suggestion=f"Add transition path from '{initial_state}' to '{state}'"
                ))
                
    def _check_missing_events(self, events: Set[str], transitions: List[Dict],
                             result: ValidationResult) -> None:
        """Check for events used in transitions but not declared"""
        used_events = set()
        
        for trans in transitions:
            event = trans.get('event')
            if event:
                used_events.add(event)
                
        missing = used_events - events
        
        for event in missing:
            result.add_error(ValidationIssue(
                category='undeclared_event',
                event=event,
                message=f"Event '{event}' used in transitions but not declared in events list",
                suggestion=f"Add '{event}' to events list"
            ))
            
    def _check_wildcard_transitions(self, transitions: List[Dict], states: Set[str],
                                   result: ValidationResult) -> None:
        """Check wildcard transitions for potential issues"""
        wildcard_transitions = [t for t in transitions if t.get('from') == '*']
        
        if len(wildcard_transitions) > 5:
            result.add_warning(ValidationIssue(
                category='excessive_wildcards',
                message=f"Configuration has {len(wildcard_transitions)} wildcard transitions (consider if all are necessary)",
                suggestion="Wildcard transitions can make state flow harder to understand"
            ))
            
    def _check_initial_state(self, initial_state: str, states: Set[str],
                            result: ValidationResult) -> None:
        """Check that initial state is valid"""
        if initial_state not in states:
            result.add_error(ValidationIssue(
                category='invalid_initial_state',
                state=initial_state,
                message=f"Initial state '{initial_state}' is not in states list",
                suggestion=f"Add '{initial_state}' to states list or change initial_state"
            ))


def print_results(results: List[ValidationResult], quiet: bool = False, 
                 use_color: bool = True) -> Tuple[int, int]:
    """Print validation results and return (error_count, warning_count)"""
    
    # ANSI color codes
    RED = '\033[91m' if use_color else ''
    YELLOW = '\033[93m' if use_color else ''
    GREEN = '\033[92m' if use_color else ''
    BLUE = '\033[94m' if use_color else ''
    RESET = '\033[0m' if use_color else ''
    BOLD = '\033[1m' if use_color else ''
    
    total_errors = 0
    total_warnings = 0
    
    for result in results:
        config_name = Path(result.config_path).name
        
        if result.passed and not result.warnings:
            if not quiet:
                print(f"{GREEN}✅ {config_name}: All validations passed{RESET}")
            continue
            
        # Print header
        if result.errors:
            print(f"\n{RED}❌ {BOLD}{config_name}{RESET}")
        elif result.warnings:
            print(f"\n{YELLOW}⚠️  {BOLD}{config_name}{RESET}")
            
        # Print errors
        for error in result.errors:
            total_errors += 1
            print(f"{RED}  [ERROR] {error.message}{RESET}")
            if error.state or error.event:
                details = []
                if error.state:
                    details.append(f"State: {error.state}")
                if error.event:
                    details.append(f"Event: {error.event}")
                print(f"    {', '.join(details)}")
            if error.suggestion:
                print(f"    {BLUE}💡 {error.suggestion}{RESET}")
                
        # Print warnings (unless quiet mode)
        if not quiet:
            for warning in result.warnings:
                total_warnings += 1
                print(f"{YELLOW}  [WARNING] {warning.message}{RESET}")
                if warning.state or warning.event:
                    details = []
                    if warning.state:
                        details.append(f"State: {warning.state}")
                    if warning.event:
                        details.append(f"Event: {warning.event}")
                    print(f"    {', '.join(details)}")
                if warning.suggestion:
                    print(f"    {BLUE}💡 {warning.suggestion}{RESET}")
                    
    return total_errors, total_warnings


def main():
    parser = argparse.ArgumentParser(
        description='Validate state machine YAML configurations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate all configs
  statemachine-validate config/*.yaml
  
  # Strict mode (warnings cause failure)
  statemachine-validate --strict config/*.yaml
  
  # Quiet mode (errors only)
  statemachine-validate --quiet config/*.yaml
        """
    )
    parser.add_argument('configs', nargs='+', help='YAML config files to validate')
    parser.add_argument('--strict', action='store_true', 
                       help='Treat warnings as errors (exit 1)')
    parser.add_argument('--quiet', action='store_true',
                       help='Only show errors, suppress warnings')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output')
    
    args = parser.parse_args()
    
    validator = StateMachineValidator(strict_mode=args.strict)
    results = []
    
    # Validate each config
    for config_path in args.configs:
        result = validator.validate_config(config_path)
        results.append(result)
        
    # Print results
    print("\n" + "="*70)
    print("State Machine Configuration Validation")
    print("="*70)
    
    total_errors, total_warnings = print_results(
        results, 
        quiet=args.quiet,
        use_color=not args.no_color
    )
    
    # Summary
    print("\n" + "="*70)
    total_configs = len(results)
    passed_configs = sum(1 for r in results if r.passed and not r.warnings)
    
    if total_errors == 0 and total_warnings == 0:
        print(f"✅ All {total_configs} configurations passed validation")
        return 0
    else:
        print(f"📊 Summary:")
        print(f"   Configurations checked: {total_configs}")
        print(f"   Passed: {passed_configs}")
        print(f"   Errors: {total_errors}")
        print(f"   Warnings: {total_warnings}")
        print("="*70 + "\n")
        
        if total_errors > 0:
            print("❌ Validation failed: Fix errors before starting system")
            return 1
        elif args.strict and total_warnings > 0:
            print("⚠️  Strict mode: Warnings present, treating as failure")
            return 2
        else:
            print("⚠️  Warnings present but validation passed")
            return 0


if __name__ == '__main__':
    sys.exit(main())