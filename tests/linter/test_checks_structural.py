"""Tests for structural checks (E001–E005)."""

from pathlib import Path

import pytest

from statemachine_engine.tools.linter.checks_structural import check_structural
from statemachine_engine.tools.linter.models import Severity

FAKE = Path("test.yaml")


def _base_config(**overrides):
    """Minimal valid config for structural tests."""
    cfg = {
        "initial_state": "idle",
        "states": ["idle", "running", "done"],
        "events": ["start", "finish"],
        "transitions": [
            {"from": "idle", "to": "running", "event": "start"},
            {"from": "running", "to": "done", "event": "finish"},
        ],
        "actions": {},
    }
    cfg.update(overrides)
    return cfg


# --- E001: initial_state not defined or not in states list ---


class TestE001:
    def test_missing_initial_state(self):
        cfg = _base_config()
        del cfg["initial_state"]
        issues = check_structural(cfg, FAKE)
        codes = [i.code for i in issues]
        assert "E001" in codes

    def test_initial_state_not_in_states(self):
        cfg = _base_config(initial_state="nonexistent")
        issues = check_structural(cfg, FAKE)
        e001 = [i for i in issues if i.code == "E001"]
        assert len(e001) == 1
        assert e001[0].severity == Severity.ERROR

    def test_valid_initial_state_no_e001(self):
        cfg = _base_config()
        issues = check_structural(cfg, FAKE)
        assert not any(i.code == "E001" for i in issues)


# --- E002: Transition references undefined state ---


class TestE002:
    def test_undefined_from_state(self):
        cfg = _base_config()
        cfg["transitions"].append(
            {"from": "ghost", "to": "idle", "event": "start"}
        )
        issues = check_structural(cfg, FAKE)
        e002 = [i for i in issues if i.code == "E002"]
        assert len(e002) >= 1
        assert "ghost" in e002[0].message

    def test_undefined_to_state(self):
        cfg = _base_config()
        cfg["transitions"].append(
            {"from": "idle", "to": "nowhere", "event": "start"}
        )
        issues = check_structural(cfg, FAKE)
        assert any(i.code == "E002" for i in issues)

    def test_wildcard_from_not_flagged(self):
        cfg = _base_config()
        cfg["transitions"].append(
            {"from": "*", "to": "done", "event": "finish"}
        )
        issues = check_structural(cfg, FAKE)
        assert not any(i.code == "E002" for i in issues)


# --- E003: Event used in transition not declared ---


class TestE003:
    def test_undeclared_event(self):
        cfg = _base_config()
        cfg["transitions"].append(
            {"from": "idle", "to": "running", "event": "phantom"}
        )
        issues = check_structural(cfg, FAKE)
        e003 = [i for i in issues if i.code == "E003"]
        assert len(e003) == 1
        assert "phantom" in e003[0].message

    def test_timeout_event_not_flagged(self):
        """timeout(30) is a synthetic event, not declared in events list."""
        cfg = _base_config()
        cfg["transitions"].append(
            {"from": "idle", "to": "running", "event": "timeout(30)"}
        )
        issues = check_structural(cfg, FAKE)
        assert not any(i.code == "E003" for i in issues)


# --- E004: Duplicate state name ---


class TestE004:
    def test_duplicate_state(self):
        cfg = _base_config(states=["idle", "running", "idle"])
        issues = check_structural(cfg, FAKE)
        e004 = [i for i in issues if i.code == "E004"]
        assert len(e004) == 1
        assert "idle" in e004[0].message

    def test_no_duplicates(self):
        cfg = _base_config()
        issues = check_structural(cfg, FAKE)
        assert not any(i.code == "E004" for i in issues)


# --- E005: Duplicate transition ---


class TestE005:
    def test_duplicate_transition(self):
        cfg = _base_config()
        cfg["transitions"].append(
            {"from": "idle", "to": "running", "event": "start"}
        )
        issues = check_structural(cfg, FAKE)
        e005 = [i for i in issues if i.code == "E005"]
        assert len(e005) == 1

    def test_same_from_event_different_to_not_duplicate(self):
        """from=idle event=start to=running vs to=done are NOT duplicates."""
        cfg = _base_config()
        cfg["transitions"].append(
            {"from": "idle", "to": "done", "event": "start"}
        )
        issues = check_structural(cfg, FAKE)
        assert not any(i.code == "E005" for i in issues)
