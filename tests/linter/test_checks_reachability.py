"""Tests for reachability checks (E006, E007, W001–W003)."""

from pathlib import Path

import pytest

from statemachine_engine.tools.linter.checks_reachability import check_reachability
from statemachine_engine.tools.linter.models import Severity

FAKE = Path("test.yaml")

TERMINAL_STATES = {"stopped", "shutdown", "completed"}


def _base_config(**overrides):
    cfg = {
        "initial_state": "idle",
        "states": ["idle", "running", "completed"],
        "events": ["start", "finish"],
        "transitions": [
            {"from": "idle", "to": "running", "event": "start"},
            {"from": "running", "to": "completed", "event": "finish"},
        ],
        "actions": {},
    }
    cfg.update(overrides)
    return cfg


# --- E006: No terminal state reachable from initial_state ---


class TestE006:
    def test_no_terminal_reachable(self):
        cfg = _base_config(
            states=["idle", "running", "stuck"],
            transitions=[
                {"from": "idle", "to": "running", "event": "start"},
                {"from": "running", "to": "stuck", "event": "finish"},
            ],
        )
        issues = check_reachability(cfg, FAKE)
        assert any(i.code == "E006" for i in issues)

    def test_terminal_reachable_no_e006(self):
        cfg = _base_config()
        issues = check_reachability(cfg, FAKE)
        assert not any(i.code == "E006" for i in issues)


# --- E007: State has no outgoing transitions and is not terminal ---


class TestE007:
    def test_dead_end_non_terminal(self):
        cfg = _base_config(
            states=["idle", "running", "stuck"],
            transitions=[
                {"from": "idle", "to": "running", "event": "start"},
                {"from": "running", "to": "stuck", "event": "finish"},
            ],
        )
        issues = check_reachability(cfg, FAKE)
        e007 = [i for i in issues if i.code == "E007"]
        assert len(e007) >= 1
        assert any("stuck" in i.message for i in e007)

    def test_terminal_state_no_outgoing_ok(self):
        """completed/stopped/shutdown are terminal — no outgoing is fine."""
        cfg = _base_config()
        issues = check_reachability(cfg, FAKE)
        assert not any(i.code == "E007" for i in issues)

    def test_wildcard_provides_outgoing(self):
        """A wildcard from: * gives every state an outgoing transition."""
        cfg = _base_config(
            states=["idle", "running", "stuck"],
            events=["start", "finish", "reset"],
            transitions=[
                {"from": "idle", "to": "running", "event": "start"},
                {"from": "running", "to": "stuck", "event": "finish"},
                {"from": "*", "to": "idle", "event": "reset"},
            ],
        )
        issues = check_reachability(cfg, FAKE)
        assert not any(i.code == "E007" for i in issues)


# --- W001: State not reachable from initial_state (orphaned) ---


class TestW001:
    def test_orphaned_state(self):
        cfg = _base_config(
            states=["idle", "running", "completed", "orphan"],
        )
        issues = check_reachability(cfg, FAKE)
        w001 = [i for i in issues if i.code == "W001"]
        assert len(w001) == 1
        assert "orphan" in w001[0].message
        assert w001[0].severity == Severity.WARNING

    def test_no_orphans(self):
        cfg = _base_config()
        issues = check_reachability(cfg, FAKE)
        assert not any(i.code == "W001" for i in issues)

    def test_wildcard_reach(self):
        """State reachable only via wildcard from: * is W002, not W001."""
        cfg = _base_config(
            states=["idle", "running", "completed", "rescue"],
            events=["start", "finish", "help"],
            transitions=[
                {"from": "idle", "to": "running", "event": "start"},
                {"from": "running", "to": "completed", "event": "finish"},
                {"from": "*", "to": "rescue", "event": "help"},
            ],
        )
        issues = check_reachability(cfg, FAKE)
        assert not any(
            i.code == "W001" and "rescue" in i.message for i in issues
        )


# --- W002: State reachable only via wildcard from: * ---


class TestW002:
    def test_wildcard_only_reach(self):
        cfg = _base_config(
            states=["idle", "running", "completed", "rescue"],
            events=["start", "finish", "help"],
            transitions=[
                {"from": "idle", "to": "running", "event": "start"},
                {"from": "running", "to": "completed", "event": "finish"},
                {"from": "*", "to": "rescue", "event": "help"},
            ],
        )
        issues = check_reachability(cfg, FAKE)
        w002 = [i for i in issues if i.code == "W002"]
        assert len(w002) >= 1
        assert any("rescue" in i.message for i in w002)

    def test_state_with_explicit_transition_no_w002(self):
        cfg = _base_config()
        issues = check_reachability(cfg, FAKE)
        assert not any(i.code == "W002" for i in issues)


# --- W003: More than 5 wildcard transitions ---


class TestW003:
    def test_excessive_wildcards(self):
        events = [f"ev{i}" for i in range(7)]
        transitions = [
            {"from": "*", "to": "idle", "event": e} for e in events
        ]
        cfg = _base_config(
            events=["start", "finish", *events],
            transitions=[
                {"from": "idle", "to": "running", "event": "start"},
                {"from": "running", "to": "completed", "event": "finish"},
                *transitions,
            ],
        )
        issues = check_reachability(cfg, FAKE)
        assert any(i.code == "W003" for i in issues)

    def test_few_wildcards_ok(self):
        cfg = _base_config(
            events=["start", "finish", "reset"],
            transitions=[
                {"from": "idle", "to": "running", "event": "start"},
                {"from": "running", "to": "completed", "event": "finish"},
                {"from": "*", "to": "idle", "event": "reset"},
            ],
        )
        issues = check_reachability(cfg, FAKE)
        assert not any(i.code == "W003" for i in issues)
