"""Compare planner report checks with the amounts stated in issue.md."""

from __future__ import annotations

import re
from decimal import Decimal

from ..schemas.task_spec import Check, TaskSpec
from .decimals import parse_decimal_string

_EXPECTED_AMOUNT = re.compile(
    r"(?i)\bexpected\b\s*[:=]\s*\$?\s*(-?\d+(?:\.\d+)?)"
)


def expected_amounts(issue_text: str) -> list[Decimal]:
    return [Decimal(match.group(1)) for match in _EXPECTED_AMOUNT.finditer(issue_text)]


def validate_report_checks(task_spec: TaskSpec, issue_text: str) -> str | None:
    """Return a planning error when report checks do not copy issue.md.

    A mismatch between planner_value and expected_value is not an error here.
    That disagreement is scored separately and does not reject the plan.
    """
    if not task_spec.checks:
        return (
            "Bug-report runs require a checks list with the Expected amounts "
            "copied from issue.md and at least one required edge case."
        )
    stated = expected_amounts(issue_text)
    if not stated:
        return "issue.md does not state any Expected amounts."
    report_checks = [check for check in task_spec.checks if check.source == "report"]
    if not report_checks:
        return "TaskSpec needs at least one source=report check copied from issue.md."
    for check in report_checks:
        value = parse_decimal_string(check.expected_value)
        if not any(value == stated_value for stated_value in stated):
            return (
                f"{check.id} expected_value {check.expected_value} is not an "
                "Expected amount in issue.md. Copy Expected amounts, not Charged amounts."
            )
    return None


def planner_accuracy(checks: list[Check] | None) -> float | None:
    if not checks:
        return None
    report_checks = [check for check in checks if check.source == "report"]
    if not report_checks:
        return None
    matched = 0
    for check in report_checks:
        if parse_decimal_string(check.planner_value) == parse_decimal_string(check.expected_value):
            matched += 1
    return matched / len(report_checks)


def planner_disagreements(checks: list[Check] | None) -> list[dict[str, str]]:
    if not checks:
        return []
    rows = []
    for check in checks:
        if check.source != "report":
            continue
        if parse_decimal_string(check.planner_value) == parse_decimal_string(check.expected_value):
            continue
        rows.append(
            {
                "id": check.id,
                "expected_value": check.expected_value,
                "planner_value": check.planner_value,
            }
        )
    return rows
