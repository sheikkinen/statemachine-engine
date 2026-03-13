"""Action checks (E008–E011, W004–W006) for FSM configs."""

from __future__ import annotations

import re
from pathlib import Path

from statemachine_engine.tools.linter.models import LintIssue, Severity

# 14 pluggable + 2 inline + 1 alias
KNOWN_ACTION_TYPES = frozenset(
    {
        # Inline (engine.py)
        "log",
        "sleep",
        # Alias
        "activity_log",
        # Pluggable built-ins
        "add_to_list",
        "bash",
        "check_database_queue",
        "check_machine_state",
        "claim_job",
        "clear_events",
        "complete_job",
        "get_pending_jobs",
        "pop_from_list",
        "send_event",
        "set_context",
        "start_fsm",
        "wait_for_jobs",
    }
)

# Required fields per action type (only types with mandatory fields)
REQUIRED_FIELDS: dict[str, list[str]] = {
    "bash": ["command"],
    "send_event": ["target_machine"],
    "complete_job": ["job_id"],
    "set_context": ["key"],
}

# Common action config keys that are valid for any action type
COMMON_ACTION_KEYS = frozenset(
    {
        "type",
        "description",
        "success",
        "failure",
        "timeout",
    }
)

# Known keys per action type (beyond common keys)
TYPE_SPECIFIC_KEYS: dict[str, frozenset[str]] = {
    "log": frozenset({"message", "level"}),
    "activity_log": frozenset({"message", "level"}),
    "sleep": frozenset({"duration"}),
    "bash": frozenset({"command"}),
    "send_event": frozenset({"target_machine", "event", "event_type", "payload"}),
    "complete_job": frozenset({"job_id", "error"}),
    "add_to_list": frozenset({"list_key", "key", "value"}),
    "pop_from_list": frozenset({"list_key", "key", "store_as", "empty"}),
    "set_context": frozenset({"key", "value"}),
    "start_fsm": frozenset(
        {
            "config",
            "yaml_path",
            "machine_name",
            "context",
            "context_vars",
            "error",
            "store_pid",
            "additional_args",
        }
    ),
    "check_database_queue": frozenset({"job_type", "machine_type"}),
    "check_machine_state": frozenset(),
    "claim_job": frozenset({"job_id", "already_claimed", "error"}),
    "clear_events": frozenset(),
    "get_pending_jobs": frozenset({"job_type", "machine_type", "store_as", "empty"}),
    "wait_for_jobs": frozenset({"tracked_jobs_key", "poll_interval", "timeout_event"}),
}

# Shell expansion patterns to flag
SHELL_EXPANSION_RE = re.compile(r"\$[A-Za-z_{\(]|`")


def _get_event_names(config: dict) -> set[str]:
    """Extract event names from either list or dict format."""
    events_raw = config.get("events", [])
    if isinstance(events_raw, dict):
        return set(events_raw.keys())
    return set(events_raw)


def _get_transition_events_from_state(transitions: list[dict], state: str) -> set[str]:
    """Get all events that have transitions FROM a given state (or wildcard)."""
    events: set[str] = set()
    for t in transitions:
        from_s = t.get("from", "")
        if from_s == state or from_s == "*":
            events.add(t.get("event", ""))
    return events


def _discover_custom_actions(config: dict, file: Path) -> set[str]:
    """Discover custom action types from actions_root directory."""
    actions_root = config.get("actions_root")
    if not actions_root:
        return set()
    root_path = (
        (file.parent / actions_root)
        if not Path(actions_root).is_absolute()
        else Path(actions_root)
    )
    custom: set[str] = set()
    if root_path.is_dir():
        for f in root_path.iterdir():
            if f.suffix == ".py" and f.stem.endswith("_action"):
                # e.g. greet_action.py → greet
                custom.add(f.stem.removesuffix("_action"))
    return custom


def check_actions(config: dict, file: Path) -> list[LintIssue]:
    """Run all action checks against an FSM config dict."""
    issues: list[LintIssue] = []
    actions = config.get("actions", {})
    transitions = config.get("transitions", [])
    events_raw = config.get("events", [])

    # Discover custom action types from actions_root
    custom_types = _discover_custom_actions(config, file)
    all_known = KNOWN_ACTION_TYPES | custom_types

    # Build set of all events that have transitions from each state
    all_transition_events: set[str] = set()
    for t in transitions:
        all_transition_events.add(t.get("event", ""))

    for state_name, action_list in actions.items():
        if not isinstance(action_list, list):
            continue
        for action in action_list:
            if not isinstance(action, dict):
                continue
            action_type = action.get("type", "")

            # E008: Action type not in known built-in types
            if action_type and action_type not in all_known:
                issues.append(
                    LintIssue(
                        code="E008",
                        severity=Severity.ERROR,
                        message=(
                            f"Unknown action type '{action_type}' in state '{state_name}'. "
                            f"Known types: {sorted(KNOWN_ACTION_TYPES)}"
                        ),
                        file=file,
                        context=state_name,
                    )
                )

            # E009: Action emits event with no corresponding transition
            for emit_key in ("success", "failure"):
                emitted = action.get(emit_key)
                if emitted and emitted not in all_transition_events:
                    issues.append(
                        LintIssue(
                            code="E009",
                            severity=Severity.ERROR,
                            message=(
                                f"Action in state '{state_name}' emits '{emitted}' "
                                f"via {emit_key} but no transition handles this event"
                            ),
                            file=file,
                            context=state_name,
                        )
                    )

            # E010: Required action config field missing
            if action_type in REQUIRED_FIELDS:
                for field in REQUIRED_FIELDS[action_type]:
                    if field not in action:
                        issues.append(
                            LintIssue(
                                code="E010",
                                severity=Severity.ERROR,
                                message=(
                                    f"Action '{action_type}' in state '{state_name}' "
                                    f"missing required field '{field}'"
                                ),
                                file=file,
                                context=state_name,
                                fix=f"Add '{field}' to the action config",
                            )
                        )

            # W004: Unknown action config keys (skip for custom action types)
            if action_type in TYPE_SPECIFIC_KEYS:
                valid_keys = COMMON_ACTION_KEYS | TYPE_SPECIFIC_KEYS[action_type]
                for key in action:
                    if key not in valid_keys:
                        issues.append(
                            LintIssue(
                                code="W004",
                                severity=Severity.WARNING,
                                message=(
                                    f"Unknown key '{key}' in '{action_type}' action "
                                    f"in state '{state_name}'"
                                ),
                                file=file,
                                context=state_name,
                            )
                        )

            # W005: sleep duration > 300s
            if action_type == "sleep":
                duration = action.get("duration", 0)
                if isinstance(duration, (int, float)) and duration > 300:
                    issues.append(
                        LintIssue(
                            code="W005",
                            severity=Severity.WARNING,
                            message=(
                                f"Sleep action in state '{state_name}' has duration "
                                f"{duration}s (> 300s threshold)"
                            ),
                            file=file,
                            context=state_name,
                        )
                    )

            # W006: bash command with unescaped shell expansion
            if action_type == "bash":
                command = action.get("command", "")
                if isinstance(command, str) and SHELL_EXPANSION_RE.search(command):
                    issues.append(
                        LintIssue(
                            code="W006",
                            severity=Severity.WARNING,
                            message=(
                                f"Bash action in state '{state_name}' contains "
                                f"shell expansion in command: {command!r}"
                            ),
                            file=file,
                            context=state_name,
                        )
                    )

    # E011: context_map key references unknown context variable
    if isinstance(events_raw, dict):
        for _event_name, event_cfg in events_raw.items():
            if isinstance(event_cfg, dict) and "context_map" in event_cfg:
                cmap = event_cfg["context_map"]
                if isinstance(cmap, dict):
                    pass  # E011 context ref checks delegated to semantic module

    return issues
