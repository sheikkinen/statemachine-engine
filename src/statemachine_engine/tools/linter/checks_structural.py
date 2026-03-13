"""Structural checks (E001–E005) for FSM configs."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from statemachine_engine.tools.linter.models import LintIssue, Severity


def check_structural(config: dict, file: Path) -> list[LintIssue]:
    """Run all structural checks against an FSM config dict."""
    issues: list[LintIssue] = []
    states = config.get("states", [])
    state_set = set(states)
    events_raw = config.get("events", [])
    # events can be list or dict (NC-120)
    event_names = (
        list(events_raw.keys()) if isinstance(events_raw, dict) else list(events_raw)
    )
    event_set = set(event_names)
    transitions = config.get("transitions", [])

    # E001: initial_state not defined or not in states list
    initial = config.get("initial_state")
    if not initial:
        issues.append(
            LintIssue(
                code="E001",
                severity=Severity.ERROR,
                message="initial_state is not defined",
                file=file,
                fix="Add 'initial_state: <state>' to the config",
            )
        )
    elif initial not in state_set:
        issues.append(
            LintIssue(
                code="E001",
                severity=Severity.ERROR,
                message=f"initial_state '{initial}' is not in the states list",
                file=file,
                context=initial,
                fix=f"Add '{initial}' to the states list or fix initial_state",
            )
        )

    # E002: Transition references undefined state
    for t in transitions:
        from_state = t.get("from", "")
        to_state = t.get("to", "")
        if from_state != "*" and from_state not in state_set:
            issues.append(
                LintIssue(
                    code="E002",
                    severity=Severity.ERROR,
                    message=(
                        f"Transition references undefined state '{from_state}' "
                        f"(from: {from_state}, to: {to_state}, event: {t.get('event', '?')})"
                    ),
                    file=file,
                    context=from_state,
                )
            )
        if to_state not in state_set:
            issues.append(
                LintIssue(
                    code="E002",
                    severity=Severity.ERROR,
                    message=(
                        f"Transition references undefined state '{to_state}' "
                        f"(from: {from_state}, to: {to_state}, event: {t.get('event', '?')})"
                    ),
                    file=file,
                    context=to_state,
                )
            )

    # E003: Event used in transition not declared in events list
    timeout_re = re.compile(r"^timeout\(\d+\)$")
    for t in transitions:
        event = t.get("event", "")
        if event and event not in event_set and not timeout_re.match(event):
            issues.append(
                LintIssue(
                    code="E003",
                    severity=Severity.ERROR,
                    message=f"Event '{event}' used in transition but not declared in events list",
                    file=file,
                    context=event,
                    fix=f"Add '{event}' to the events list",
                )
            )

    # E004: Duplicate state name
    counts = Counter(states)
    for state, count in counts.items():
        if count > 1:
            issues.append(
                LintIssue(
                    code="E004",
                    severity=Severity.ERROR,
                    message=f"Duplicate state name '{state}' (appears {count} times)",
                    file=file,
                    context=state,
                )
            )

    # E005: Duplicate transition (same from + event + to)
    seen: set[tuple[str, str, str]] = set()
    for t in transitions:
        key = (t.get("from", ""), t.get("to", ""), t.get("event", ""))
        if key in seen:
            issues.append(
                LintIssue(
                    code="E005",
                    severity=Severity.ERROR,
                    message=(
                        f"Duplicate transition: from={key[0]} to={key[1]} event={key[2]}"
                    ),
                    file=file,
                )
            )
        seen.add(key)

    return issues
