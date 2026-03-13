"""Reachability checks (E006, E007, W001–W003) for FSM configs."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from statemachine_engine.tools.linter.models import LintIssue, Severity

TERMINAL_STATES = frozenset({"stopped", "shutdown", "completed"})


def _build_adjacency(transitions: list[dict], states: list[str]) -> dict[str, set[str]]:
    """Build adjacency list from transitions. Wildcards expand to all states."""
    adj: dict[str, set[str]] = defaultdict(set)
    for t in transitions:
        from_state = t.get("from", "")
        to_state = t.get("to", "")
        if from_state == "*":
            for s in states:
                adj[s].add(to_state)
        else:
            adj[from_state].add(to_state)
    return adj


def _reachable_from(start: str, adj: dict[str, set[str]]) -> set[str]:
    """BFS to find all states reachable from start."""
    visited: set[str] = set()
    queue = [start]
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        for neighbor in adj.get(current, set()):
            if neighbor not in visited:
                queue.append(neighbor)
    return visited


def check_reachability(config: dict, file: Path) -> list[LintIssue]:
    """Run all reachability checks against an FSM config dict."""
    issues: list[LintIssue] = []
    states = config.get("states", [])
    transitions = config.get("transitions", [])
    initial = config.get("initial_state", "")

    adj = _build_adjacency(transitions, states)
    reachable = _reachable_from(initial, adj) if initial else set()

    # Track which states have explicit (non-wildcard) incoming transitions
    explicit_targets: set[str] = set()
    wildcard_targets: set[str] = set()
    for t in transitions:
        to_state = t.get("to", "")
        if t.get("from", "") == "*":
            wildcard_targets.add(to_state)
        else:
            explicit_targets.add(to_state)

    # Track outgoing transitions per state (including wildcards)
    has_outgoing: set[str] = set()
    for t in transitions:
        from_state = t.get("from", "")
        if from_state == "*":
            # Wildcard gives every state an outgoing transition
            has_outgoing.update(states)
        else:
            has_outgoing.add(from_state)

    # E006: No terminal state reachable from initial_state
    if initial and not (reachable & TERMINAL_STATES):
        issues.append(
            LintIssue(
                code="E006",
                severity=Severity.ERROR,
                message=(
                    f"No terminal state reachable from initial_state '{initial}'. "
                    f"Terminal states: {sorted(TERMINAL_STATES)}"
                ),
                file=file,
                context=initial,
            )
        )

    # E007: State has no outgoing transitions and is not terminal
    for state in states:
        if state not in has_outgoing and state not in TERMINAL_STATES:
            issues.append(
                LintIssue(
                    code="E007",
                    severity=Severity.ERROR,
                    message=(
                        f"State '{state}' has no outgoing transitions and is not "
                        f"a terminal state (stopped/shutdown/completed)"
                    ),
                    file=file,
                    context=state,
                )
            )

    # W001: State not reachable from initial_state (orphaned)
    for state in states:
        if state != initial and state not in reachable:
            issues.append(
                LintIssue(
                    code="W001",
                    severity=Severity.WARNING,
                    message=f"State '{state}' not reachable from initial state '{initial}'",
                    file=file,
                    context=state,
                )
            )

    # W002: State reachable only via wildcard from: *
    for state in states:
        if state == initial:
            continue
        if (
            state in reachable
            and state in wildcard_targets
            and state not in explicit_targets
        ):
            issues.append(
                LintIssue(
                    code="W002",
                    severity=Severity.WARNING,
                    message=f"State '{state}' reachable only via wildcard 'from: *'",
                    file=file,
                    context=state,
                )
            )

    # W003: More than 5 wildcard transitions
    wildcard_count = sum(1 for t in transitions if t.get("from") == "*")
    if wildcard_count > 5:
        issues.append(
            LintIssue(
                code="W003",
                severity=Severity.WARNING,
                message=f"Config has {wildcard_count} wildcard transitions (threshold: 5)",
                file=file,
            )
        )

    return issues
