"""CLI entry point for statemachine-lint."""

from __future__ import annotations

import argparse
import json
import sys

from statemachine_engine.tools.linter.core import run_linter
from statemachine_engine.tools.linter.models import Severity


def cli_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="statemachine-lint",
        description="Lint FSM YAML state machine configurations",
    )
    parser.add_argument("files", nargs="+", help="YAML config files to lint")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="output_format",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--select",
        help="Comma-separated list of check codes to run (e.g., E001,E002,W001)",
    )
    args = parser.parse_args(argv)

    selected_codes = None
    if args.select:
        selected_codes = set(args.select.split(","))

    total_errors = 0
    total_warnings = 0
    all_results = []

    for filepath in args.files:
        result = run_linter(filepath, strict=args.strict)

        if selected_codes:
            result.issues = [i for i in result.issues if i.code in selected_codes]
            result.error_count = sum(
                1 for i in result.issues if i.severity == Severity.ERROR
            )
            result.warning_count = sum(
                1 for i in result.issues if i.severity == Severity.WARNING
            )

        total_errors += result.error_count
        total_warnings += result.warning_count

        if args.output_format == "json":
            all_results.append(
                {
                    "file": filepath,
                    "issues": [i.model_dump(mode="json") for i in result.issues],
                    "error_count": result.error_count,
                    "warning_count": result.warning_count,
                }
            )
        else:
            if result.issues:
                print(f"\n{filepath}")
                for issue in result.issues:
                    icon = "\u2717" if issue.severity == Severity.ERROR else "\u26a0"
                    print(f"  {icon} [{issue.code}] {issue.message}")
                    if issue.fix:
                        print(f"    \u2192 {issue.fix}")

    if args.output_format == "json":
        print(json.dumps(all_results, indent=2))
    else:
        print(f"\n{total_errors} errors, {total_warnings} warnings")

    sys.exit(1 if total_errors > 0 else 0)
