"""Tests for semantic & cross-reference checks (E012–E015, W007–W010)."""

from pathlib import Path

import pytest

from statemachine_engine.tools.linter.checks_semantic import check_semantic
from statemachine_engine.tools.linter.models import Severity

FAKE = Path("test.yaml")


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


# --- E012: {variable} interpolation references undeclared context key ---


class TestE012:
    def test_undeclared_interpolation_var(self):
        """Action uses {foo} but 'foo' is not a standard engine context key."""
        cfg = _base_config(
            actions={
                "idle": [
                    {"type": "log", "message": "Processing {nonexistent_var}"}
                ],
            }
        )
        issues = check_semantic(cfg, FAKE)
        e012 = [i for i in issues if i.code == "E012"]
        assert len(e012) >= 1
        assert "nonexistent_var" in e012[0].message

    def test_known_context_keys_ok(self):
        """Standard engine context keys like id, job_id, machine_name are ok."""
        cfg = _base_config(
            actions={
                "idle": [
                    {"type": "log", "message": "Job {id} on {machine_name}"}
                ],
            }
        )
        issues = check_semantic(cfg, FAKE)
        assert not any(i.code == "E012" for i in issues)

    def test_context_map_promoted_key_ok(self):
        """Keys promoted via context_map are known context keys."""
        cfg = _base_config(
            events={
                "start": {"context_map": {"user_input": "payload.text"}},
                "finish": {},
            },
            actions={
                "running": [
                    {"type": "log", "message": "Got: {user_input}"}
                ],
            },
        )
        issues = check_semantic(cfg, FAKE)
        assert not any(i.code == "E012" for i in issues)


# --- E013: context_map payload path uses invalid syntax ---


class TestE013:
    def test_invalid_payload_path(self):
        cfg = _base_config(
            events={
                "start": {"context_map": {"key": "not-a-valid..path"}},
                "finish": {},
            }
        )
        issues = check_semantic(cfg, FAKE)
        e013 = [i for i in issues if i.code == "E013"]
        assert len(e013) >= 1

    def test_valid_payload_path(self):
        cfg = _base_config(
            events={
                "start": {"context_map": {"key": "payload.data.field"}},
                "finish": {},
            }
        )
        issues = check_semantic(cfg, FAKE)
        assert not any(i.code == "E013" for i in issues)


# --- E014: context_map payload path too deep ---


class TestE014:
    def test_excessively_deep_path(self):
        cfg = _base_config(
            events={
                "start": {
                    "context_map": {
                        "key": "payload.a.b.c.d.e.f.g.h"
                    }
                },
                "finish": {},
            }
        )
        issues = check_semantic(cfg, FAKE)
        e014 = [i for i in issues if i.code == "E014"]
        assert len(e014) >= 1

    def test_reasonable_depth_ok(self):
        cfg = _base_config(
            events={
                "start": {"context_map": {"key": "payload.data.field"}},
                "finish": {},
            }
        )
        issues = check_semantic(cfg, FAKE)
        assert not any(i.code == "E014" for i in issues)


# --- E015: Circular context_map dependency ---


class TestE015:
    def test_circular_dependency(self):
        """Event A promotes 'x' from payload, event B promotes 'y' from 'x'
        — this is NOT circular. Circular requires A promotes from B's output
        and B promotes from A's output in a cycle."""
        cfg = _base_config(
            states=["idle", "step_a", "step_b", "completed"],
            events={
                "start": {"context_map": {"x": "payload.input"}},
                "go_b": {"context_map": {"y": "payload.x_result"}},
                "finish": {},
            },
            transitions=[
                {"from": "idle", "to": "step_a", "event": "start"},
                {"from": "step_a", "to": "step_b", "event": "go_b"},
                {"from": "step_b", "to": "completed", "event": "finish"},
            ],
        )
        issues = check_semantic(cfg, FAKE)
        assert not any(i.code == "E015" for i in issues)


# --- W007: Event declared but never used in any transition ---


class TestW007:
    def test_unused_event(self):
        cfg = _base_config(
            events=["start", "finish", "orphan_event"],
        )
        issues = check_semantic(cfg, FAKE)
        w007 = [i for i in issues if i.code == "W007"]
        assert len(w007) == 1
        assert "orphan_event" in w007[0].message

    def test_all_events_used(self):
        cfg = _base_config()
        issues = check_semantic(cfg, FAKE)
        assert not any(i.code == "W007" for i in issues)

    def test_dict_events_unused(self):
        """Dict-format events should also be checked for usage."""
        cfg = _base_config(
            events={
                "start": {},
                "finish": {},
                "unused": {},
            }
        )
        issues = check_semantic(cfg, FAKE)
        w007 = [i for i in issues if i.code == "W007"]
        assert len(w007) == 1
        assert "unused" in w007[0].message


# --- W008: State has actions but all paths exit via error only ---


class TestW008:
    def test_error_only_exit(self):
        cfg = _base_config(
            states=["idle", "processing", "error_state", "completed"],
            events=["start", "error", "finish"],
            transitions=[
                {"from": "idle", "to": "processing", "event": "start"},
                {"from": "processing", "to": "error_state", "event": "error"},
                {"from": "error_state", "to": "completed", "event": "finish"},
            ],
            actions={
                "processing": [
                    {"type": "bash", "command": "echo", "failure": "error"}
                ],
            },
        )
        issues = check_semantic(cfg, FAKE)
        w008 = [i for i in issues if i.code == "W008"]
        assert len(w008) >= 1

    def test_happy_path_exists(self):
        cfg = _base_config(
            actions={
                "idle": [
                    {"type": "bash", "command": "echo", "success": "start"}
                ],
            }
        )
        issues = check_semantic(cfg, FAKE)
        assert not any(i.code == "W008" for i in issues)


# --- W009: Interpolation used but no event promotes variable via context_map ---


class TestW009:
    def test_unpromoted_variable(self):
        """Using {report_id} with no context_map promoting it."""
        cfg = _base_config(
            actions={
                "idle": [
                    {"type": "log", "message": "Report: {report_id}"}
                ],
            },
        )
        issues = check_semantic(cfg, FAKE)
        w009 = [i for i in issues if i.code == "W009"]
        # W009 fires for non-standard keys that aren't promoted
        assert len(w009) >= 1

    def test_promoted_variable_ok(self):
        """context_map promotes 'report_id' → no W009."""
        cfg = _base_config(
            events={
                "start": {"context_map": {"report_id": "payload.report_id"}},
                "finish": {},
            },
            actions={
                "running": [
                    {"type": "log", "message": "Report: {report_id}"}
                ],
            },
        )
        issues = check_semantic(cfg, FAKE)
        assert not any(i.code == "W009" for i in issues)


# --- W010: Self-transition without action (infinite idle loop) ---


class TestW010:
    def test_self_transition_no_action(self):
        cfg = _base_config(
            transitions=[
                {"from": "idle", "to": "running", "event": "start"},
                {"from": "running", "to": "completed", "event": "finish"},
                {"from": "idle", "to": "idle", "event": "start"},
            ],
        )
        issues = check_semantic(cfg, FAKE)
        w010 = [i for i in issues if i.code == "W010"]
        assert len(w010) >= 1

    def test_self_transition_with_action_ok(self):
        cfg = _base_config(
            transitions=[
                {"from": "idle", "to": "running", "event": "start"},
                {"from": "running", "to": "completed", "event": "finish"},
                {"from": "idle", "to": "idle", "event": "start"},
            ],
            actions={
                "idle": [{"type": "log", "message": "retrying"}],
            },
        )
        issues = check_semantic(cfg, FAKE)
        assert not any(i.code == "W010" for i in issues)
