"""Data models for the FSM graph linter."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class LintIssue(BaseModel):
    code: str
    severity: Severity
    message: str
    file: Path
    context: str | None = None
    fix: str | None = None


class LintResult(BaseModel):
    issues: list[LintIssue]
    error_count: int = 0
    warning_count: int = 0
