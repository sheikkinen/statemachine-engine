"""FSM Graph Linter — static analysis for state machine YAML configs."""

from statemachine_engine.tools.linter.models import LintIssue, LintResult, Severity

__all__ = ["LintIssue", "LintResult", "Severity", "lint_config", "main"]


def lint_config(config_path: str, strict: bool = False) -> LintResult:
    """Lint a single FSM config file. Delegates to core.run_linter."""
    from statemachine_engine.tools.linter.core import run_linter

    return run_linter(config_path, strict=strict)


def main():
    """CLI entry point for statemachine-lint."""
    from statemachine_engine.tools.linter.cli import cli_main

    cli_main()
