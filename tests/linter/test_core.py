"""Tests for the linter core orchestrator and CLI."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from statemachine_engine.tools.linter import lint_config
from statemachine_engine.tools.linter.models import LintIssue, LintResult, Severity


class TestLintResult:
    def test_pydantic_model(self):
        issue = LintIssue(
            code="E001",
            severity=Severity.ERROR,
            message="test",
            file=Path("test.yaml"),
        )
        result = LintResult(
            issues=[issue],
            error_count=1,
            warning_count=0,
        )
        assert result.error_count == 1
        assert len(result.issues) == 1
        assert result.issues[0].code == "E001"

    def test_issue_with_context_and_fix(self):
        issue = LintIssue(
            code="W001",
            severity=Severity.WARNING,
            message="orphaned state",
            file=Path("test.yaml"),
            context="orphan_state",
            fix="Remove unused state",
        )
        assert issue.context == "orphan_state"
        assert issue.fix == "Remove unused state"


class TestLintConfig:
    def test_lint_valid_config(self, tmp_path):
        """A minimal valid config should lint cleanly."""
        config = tmp_path / "valid.yaml"
        config.write_text(
            """
initial_state: idle
states:
  - idle
  - completed
events:
  - done
transitions:
  - from: idle
    to: completed
    event: done
actions:
  idle:
    - type: log
      message: "hello"
"""
        )
        result = lint_config(str(config))
        assert result.error_count == 0

    def test_lint_catches_errors(self, tmp_path):
        """Config with E001 (bad initial_state) should have errors."""
        config = tmp_path / "bad.yaml"
        config.write_text(
            """
initial_state: nonexistent
states:
  - idle
  - completed
events:
  - done
transitions:
  - from: idle
    to: completed
    event: done
actions: {}
"""
        )
        result = lint_config(str(config))
        assert result.error_count > 0
        assert any(i.code == "E001" for i in result.issues)
