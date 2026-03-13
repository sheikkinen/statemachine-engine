"""Linter core orchestrator — loads config, runs all checks, returns LintResult."""

from __future__ import annotations

from pathlib import Path

import yaml

from statemachine_engine.tools.linter.checks_actions import check_actions
from statemachine_engine.tools.linter.checks_reachability import check_reachability
from statemachine_engine.tools.linter.checks_semantic import check_semantic
from statemachine_engine.tools.linter.checks_structural import check_structural
from statemachine_engine.tools.linter.models import LintResult, Severity


def run_linter(config_path: str, strict: bool = False) -> LintResult:
    """Load an FSM YAML config and run all lint checks."""
    path = Path(config_path)
    with open(path) as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        from statemachine_engine.tools.linter.models import LintIssue

        return LintResult(
            issues=[
                LintIssue(
                    code="E000",
                    severity=Severity.ERROR,
                    message="Config file does not contain a YAML mapping",
                    file=path,
                )
            ],
            error_count=1,
            warning_count=0,
        )

    return run_checks(config, path, strict=strict)


def run_checks(config: dict, file: Path, strict: bool = False) -> LintResult:
    """Run all check modules against an already-parsed config dict."""
    issues = []
    issues.extend(check_structural(config, file))
    issues.extend(check_reachability(config, file))
    issues.extend(check_actions(config, file))
    issues.extend(check_semantic(config, file))

    error_count = sum(1 for i in issues if i.severity == Severity.ERROR)
    warning_count = sum(1 for i in issues if i.severity == Severity.WARNING)

    if strict:
        error_count += warning_count

    return LintResult(
        issues=issues,
        error_count=error_count,
        warning_count=warning_count,
    )
