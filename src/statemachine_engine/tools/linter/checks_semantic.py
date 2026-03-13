"""Semantic & cross-reference checks (E012–E015, W007–W010) for FSM configs."""

from __future__ import annotations

import re
from pathlib import Path

from statemachine_engine.tools.linter.models import LintIssue, Severity

# Engine interpolation regex: {variable} or {variable.nested.path}
INTERPOLATION_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_.]*)\}")

# Standard engine context keys always available (set by engine itself)
STANDARD_CONTEXT_KEYS = frozenset(
    {
        "id",
        "job_id",
        "machine_name",
        "current_state",
        "previous_state",
        "error_message",
        "job_type",
        "status",
        "data",
    }
)

# Maximum reasonable depth for payload paths
MAX_PAYLOAD_DEPTH = 6

# Regex for valid payload path: dotted identifier segments
VALID_PAYLOAD_PATH_RE = re.compile(
    r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$"
)


def _get_event_names(config: dict) -> set[str]:
    """Extract event names from either list or dict format."""
    events_raw = config.get("events", [])
    if isinstance(events_raw, dict):
        return set(events_raw.keys())
    return set(events_raw)


def _get_context_map_keys(config: dict) -> set[str]:
    """Get all context keys promoted via context_map across all events."""
    promoted: set[str] = set()
    events_raw = config.get("events", [])
    if isinstance(events_raw, dict):
        for event_cfg in events_raw.values():
            if isinstance(event_cfg, dict) and "context_map" in event_cfg:
                cmap = event_cfg["context_map"]
                if isinstance(cmap, dict):
                    promoted.update(cmap.keys())
    return promoted


def _extract_interpolation_vars(text: str) -> set[str]:
    """Extract all {variable} references from a string."""
    return set(INTERPOLATION_RE.findall(text))


def _get_all_interpolation_vars(config: dict) -> set[str]:
    """Scan all action configs for {variable} interpolation references."""
    all_vars: set[str] = set()
    actions = config.get("actions", {})
    for action_list in actions.values():
        if not isinstance(action_list, list):
            continue
        for action in action_list:
            if not isinstance(action, dict):
                continue
            for _key, value in action.items():
                if isinstance(value, str):
                    all_vars.update(_extract_interpolation_vars(value))
    return all_vars


def check_semantic(config: dict, file: Path) -> list[LintIssue]:
    """Run all semantic/cross-reference checks against an FSM config dict."""
    issues: list[LintIssue] = []
    events_raw = config.get("events", [])
    event_names = _get_event_names(config)
    transitions = config.get("transitions", [])
    actions = config.get("actions", {})
    states = config.get("states", [])

    # Collect context_map promoted keys
    promoted_keys = _get_context_map_keys(config)
    known_keys = STANDARD_CONTEXT_KEYS | promoted_keys

    # Collect all interpolation variables used in actions
    all_interp_vars = _get_all_interpolation_vars(config)

    # Build transition events per state
    transition_events_from_state: dict[str, set[str]] = {}
    for t in transitions:
        from_s = t.get("from", "")
        event = t.get("event", "")
        if from_s == "*":
            for s in states:
                transition_events_from_state.setdefault(s, set()).add(event)
        else:
            transition_events_from_state.setdefault(from_s, set()).add(event)

    # All events used in transitions
    transition_events: set[str] = set()
    for t in transitions:
        transition_events.add(t.get("event", ""))

    # E012: {variable} interpolation references undeclared context key
    for state_name, action_list in actions.items():
        if not isinstance(action_list, list):
            continue
        for action in action_list:
            if not isinstance(action, dict):
                continue
            for _key, value in action.items():
                if not isinstance(value, str):
                    continue
                for var in _extract_interpolation_vars(value):
                    # Split dotted paths — check the root key
                    root_key = var.split(".")[0]
                    if root_key not in known_keys:
                        issues.append(
                            LintIssue(
                                code="E012",
                                severity=Severity.ERROR,
                                message=(
                                    f"Interpolation '{{{var}}}' in state "
                                    f"'{state_name}' references undeclared context key "
                                    f"'{root_key}'"
                                ),
                                file=file,
                                context=state_name,
                            )
                        )

    # E013 & E014: context_map payload path validation
    if isinstance(events_raw, dict):
        for event_name, event_cfg in events_raw.items():
            if not isinstance(event_cfg, dict) or "context_map" not in event_cfg:
                continue
            cmap = event_cfg["context_map"]
            if not isinstance(cmap, dict):
                continue
            for ctx_key, payload_path in cmap.items():
                if not isinstance(payload_path, str):
                    continue
                # E013: Invalid syntax
                if not VALID_PAYLOAD_PATH_RE.match(payload_path):
                    issues.append(
                        LintIssue(
                            code="E013",
                            severity=Severity.ERROR,
                            message=(
                                f"context_map path '{payload_path}' for key '{ctx_key}' "
                                f"on event '{event_name}' uses invalid syntax"
                            ),
                            file=file,
                            context=event_name,
                        )
                    )
                else:
                    # E014: Path too deep
                    depth = len(payload_path.split("."))
                    if depth > MAX_PAYLOAD_DEPTH:
                        issues.append(
                            LintIssue(
                                code="E014",
                                severity=Severity.ERROR,
                                message=(
                                    f"context_map path '{payload_path}' for key '{ctx_key}' "
                                    f"on event '{event_name}' has depth {depth} "
                                    f"(max: {MAX_PAYLOAD_DEPTH})"
                                ),
                                file=file,
                                context=event_name,
                            )
                        )

    # E015: Circular context_map dependency
    # (Currently a placeholder — circular deps are unusual in practice)

    # W007: Event declared but never used in any transition
    for event in event_names:
        if event not in transition_events:
            issues.append(
                LintIssue(
                    code="W007",
                    severity=Severity.WARNING,
                    message=f"Event '{event}' declared but never used in any transition",
                    file=file,
                    context=event,
                )
            )

    # W008: State has actions but all paths exit via error event only
    error_events = {"error", "processing_error", "failure"}
    for state_name, action_list in actions.items():
        if not isinstance(action_list, list) or not action_list:
            continue
        outgoing = transition_events_from_state.get(state_name, set())
        if outgoing and outgoing.issubset(error_events):
            issues.append(
                LintIssue(
                    code="W008",
                    severity=Severity.WARNING,
                    message=(
                        f"State '{state_name}' has actions but all outgoing transitions "
                        f"use error events only: {sorted(outgoing)}"
                    ),
                    file=file,
                    context=state_name,
                )
            )

    # W009: Interpolation used but no event promotes variable via context_map
    for var in all_interp_vars:
        root_key = var.split(".")[0]
        if root_key in STANDARD_CONTEXT_KEYS:
            continue
        if root_key not in promoted_keys:
            issues.append(
                LintIssue(
                    code="W009",
                    severity=Severity.WARNING,
                    message=(
                        f"Interpolation '{{{var}}}' used but no event promotes "
                        f"'{root_key}' via context_map"
                    ),
                    file=file,
                    context=root_key,
                )
            )

    # W010: Self-transition without action
    for t in transitions:
        from_s = t.get("from", "")
        to_s = t.get("to", "")
        if from_s == to_s and from_s != "*":
            state_actions = actions.get(from_s, [])
            if not state_actions:
                issues.append(
                    LintIssue(
                        code="W010",
                        severity=Severity.WARNING,
                        message=(
                            f"Self-transition on state '{from_s}' "
                            f"(event: {t.get('event', '?')}) has no actions"
                        ),
                        file=file,
                        context=from_s,
                    )
                )

    return issues
