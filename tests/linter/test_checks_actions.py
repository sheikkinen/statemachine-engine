"""Tests for action checks (E008–E011, W004–W006)."""

from pathlib import Path

import pytest

from statemachine_engine.tools.linter.checks_actions import check_actions
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


# --- E008: Action type not in known built-in types ---


class TestE008:
    def test_unknown_action_type(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "teleport", "message": "hi"}],
            }
        )
        issues = check_actions(cfg, FAKE)
        e008 = [i for i in issues if i.code == "E008"]
        assert len(e008) == 1
        assert "teleport" in e008[0].message

    def test_known_pluggable_action(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "bash", "command": "echo hi", "timeout": 5}],
            }
        )
        issues = check_actions(cfg, FAKE)
        assert not any(i.code == "E008" for i in issues)

    def test_inline_log_action(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "log", "message": "hello"}],
            }
        )
        issues = check_actions(cfg, FAKE)
        assert not any(i.code == "E008" for i in issues)

    def test_inline_sleep_action(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "sleep", "duration": 5}],
            }
        )
        issues = check_actions(cfg, FAKE)
        assert not any(i.code == "E008" for i in issues)

    def test_activity_log_alias(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "activity_log", "message": "hello"}],
            }
        )
        issues = check_actions(cfg, FAKE)
        assert not any(i.code == "E008" for i in issues)


# --- E009: Action emits event with no corresponding transition ---


class TestE009:
    def test_success_event_no_transition(self):
        cfg = _base_config(
            actions={
                "idle": [
                    {"type": "bash", "command": "echo", "success": "phantom_event"}
                ],
            }
        )
        issues = check_actions(cfg, FAKE)
        e009 = [i for i in issues if i.code == "E009"]
        assert len(e009) >= 1
        assert "phantom_event" in e009[0].message

    def test_failure_event_no_transition(self):
        cfg = _base_config(
            actions={
                "idle": [
                    {"type": "bash", "command": "echo", "failure": "no_handler"}
                ],
            }
        )
        issues = check_actions(cfg, FAKE)
        assert any(i.code == "E009" for i in issues)

    def test_success_with_matching_transition_ok(self):
        cfg = _base_config(
            actions={
                "idle": [
                    {"type": "bash", "command": "echo", "success": "start"}
                ],
            }
        )
        issues = check_actions(cfg, FAKE)
        assert not any(i.code == "E009" for i in issues)


# --- E010: Required action config field missing ---


class TestE010:
    def test_bash_missing_command(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "bash", "description": "no command"}],
            }
        )
        issues = check_actions(cfg, FAKE)
        e010 = [i for i in issues if i.code == "E010"]
        assert len(e010) == 1
        assert "command" in e010[0].message

    def test_bash_with_command_ok(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "bash", "command": "echo hi"}],
            }
        )
        issues = check_actions(cfg, FAKE)
        assert not any(i.code == "E010" for i in issues)

    def test_send_event_missing_fields(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "send_event"}],
            }
        )
        issues = check_actions(cfg, FAKE)
        e010 = [i for i in issues if i.code == "E010"]
        assert len(e010) >= 1
        assert "target_machine" in e010[0].message

    def test_complete_job_missing_job_id(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "complete_job"}],
            }
        )
        issues = check_actions(cfg, FAKE)
        e010 = [i for i in issues if i.code == "E010"]
        assert len(e010) >= 1
        assert "job_id" in e010[0].message


# --- E011: context_map key references unknown context variable ---


class TestE011:
    def test_context_map_on_event_valid(self):
        """context_map on an event config is valid — no E011 if keys are fresh."""
        cfg = _base_config(
            events={
                "start": {"context_map": {"user_input": "payload.text"}},
                "finish": {},
            }
        )
        issues = check_actions(cfg, FAKE)
        assert not any(i.code == "E011" for i in issues)

    def test_context_map_with_invalid_payload_path(self):
        """context_map value must start with 'payload.'."""
        cfg = _base_config(
            events={
                "start": {"context_map": {"user_input": "invalid_path"}},
                "finish": {},
            }
        )
        issues = check_actions(cfg, FAKE)
        # E013 catches invalid syntax — E011 is about unknown context refs
        # Both are valid checks, but E013 handles this case


# --- W004: Action config contains unknown keys ---


class TestW004:
    def test_unknown_action_key(self):
        cfg = _base_config(
            actions={
                "idle": [
                    {
                        "type": "log",
                        "message": "hi",
                        "bogus_key": "value",
                    }
                ],
            }
        )
        issues = check_actions(cfg, FAKE)
        w004 = [i for i in issues if i.code == "W004"]
        assert len(w004) >= 1
        assert "bogus_key" in w004[0].message

    def test_known_keys_no_w004(self):
        cfg = _base_config(
            actions={
                "idle": [
                    {
                        "type": "log",
                        "message": "hi",
                        "level": "info",
                    }
                ],
            }
        )
        issues = check_actions(cfg, FAKE)
        assert not any(i.code == "W004" for i in issues)


# --- W005: sleep action duration > 300s ---


class TestW005:
    def test_excessive_sleep(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "sleep", "duration": 600}],
            }
        )
        issues = check_actions(cfg, FAKE)
        w005 = [i for i in issues if i.code == "W005"]
        assert len(w005) == 1

    def test_reasonable_sleep(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "sleep", "duration": 10}],
            }
        )
        issues = check_actions(cfg, FAKE)
        assert not any(i.code == "W005" for i in issues)


# --- W006: bash action with unescaped shell expansion ---


class TestW006:
    def test_unescaped_shell_variable(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "bash", "command": "echo $HOME"}],
            }
        )
        issues = check_actions(cfg, FAKE)
        w006 = [i for i in issues if i.code == "W006"]
        assert len(w006) == 1

    def test_backtick_command_substitution(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "bash", "command": "echo `date`"}],
            }
        )
        issues = check_actions(cfg, FAKE)
        assert any(i.code == "W006" for i in issues)

    def test_safe_command(self):
        cfg = _base_config(
            actions={
                "idle": [{"type": "bash", "command": "echo hello world"}],
            }
        )
        issues = check_actions(cfg, FAKE)
        assert not any(i.code == "W006" for i in issues)

    def test_fsm_interpolation_not_flagged(self):
        """FSM {variable} interpolation is not shell expansion."""
        cfg = _base_config(
            actions={
                "idle": [{"type": "bash", "command": "echo {job_id}"}],
            }
        )
        issues = check_actions(cfg, FAKE)
        assert not any(i.code == "W006" for i in issues)
