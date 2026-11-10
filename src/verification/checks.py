"""Match TaskSpec checks to expected values asserted by passing tests."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from ..schemas.task_spec import Check
from .assertions import assertion_hits, load_test_sources
from .decimals import parse_decimal_string
from .runner import passed_test_names, run_pytest


def verify_checks(workspace: str, checks: Sequence[Check]) -> dict[str, Any]:
    outcome = run_pytest(workspace)
    passed_names = passed_test_names(outcome.junit_xml)
    hits = []
    for path, source in load_test_sources(workspace):
        hits.extend(assertion_hits(source, path))
    passing_hits = [hit for hit in hits if hit.function_name in passed_names]

    details = []
    unmatched: list[str] = []
    for check in checks:
        expected = parse_decimal_string(check.expected_value)
        match = next((hit for hit in passing_hits if hit.value == expected), None)
        passed = match is not None
        if passed and match is not None:
            details_text = f"{match.path}:{match.line} {match.text}"
        else:
            details_text = "Expected value was not asserted in a passing test"
            unmatched.append(
                f"{check.id} ({check.source}, required={str(check.required).lower()}) "
                f"expected {check.expected_value}"
            )
        details.append(
            {
                "id": check.id,
                "source": check.source,
                "description": check.description,
                "expected_value": check.expected_value,
                "planner_value": check.planner_value,
                "required": check.required,
                "reason": check.reason,
                "passed": passed,
                "criterion": check.description,
                "details": details_text,
                "assertion": None
                if match is None
                else {"path": match.path, "line": match.line, "text": match.text},
                "verification_method": "pytest_assert",
                "kind": "check",
            }
        )

    required = [row for row in details if row["required"]]
    optional = [row for row in details if not row["required"]]
    required_passed = sum(1 for row in required if row["passed"])
    criteria_passed = bool(required) and required_passed == len(required)
    return {
        "criteria_passed": criteria_passed,
        "criteria_pass_rate": (required_passed / len(required)) if required else 0.0,
        "verified_criteria": required_passed,
        "total_criteria": len(required),
        "optional_passed": sum(1 for row in optional if row["passed"]),
        "optional_total": len(optional),
        "details": details,
        "checks": details,
        "unmatched": unmatched,
        "pytest": {
            "returncode": outcome.returncode,
            "output": outcome.output[:4000],
            "sandbox": outcome.sandbox,
            "warning": outcome.warning,
            "error": outcome.error,
        },
    }
