"""Acceptance checks against a generated workspace.

Numeric expectations pass only when a passing pytest assertion contains that
number. A missing assertion is a failure. File existence and pytest-pass
criteria use the filesystem and the pytest result. Other criteria stay
failed instead of inheriting an overall pass flag.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Sequence

from src.verification.assertions import assertion_hits, load_test_sources
from src.verification.decimals import parse_decimal_string
from src.verification.runner import passed_test_names, run_pytest

_EXPECTED_NUMBER = re.compile(
    r"(?:==|expected\s*[:=]?)\s*\$?\s*(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_PY_FILE = re.compile(r"([A-Za-z0-9_./-]+\.py)")
_EXISTENCE_WORDS = {"exist", "exists", "created", "present"}


def expected_numbers(criterion: str) -> List[Decimal]:
    """Decimal values a criterion requires a passing test to assert."""
    found: List[Decimal] = []
    for match in _EXPECTED_NUMBER.finditer(criterion):
        found.append(parse_decimal_string(match.group(1)))
    return found


def verify_workspace_criteria(
    workspace: str,
    criteria: Sequence[str],
) -> Dict[str, Any]:
    """Judge each acceptance criterion from the workspace on disk."""
    outcome = run_pytest(workspace)
    passed_names = passed_test_names(outcome.junit_xml)
    hits = []
    for path, source in load_test_sources(workspace):
        hits.extend(assertion_hits(source, path))
    passing_hits = [hit for hit in hits if hit.function_name in passed_names]
    collected = _collected_tests(outcome.returncode, outcome.junit_xml)
    pytest_passed = outcome.returncode == 0 and collected

    details: Dict[str, bool] = {}
    evidence: List[Dict[str, Any]] = []
    misses: List[str] = []
    for criterion in criteria:
        passed, method, text = _judge_criterion(
            workspace,
            criterion,
            passing_hits=passing_hits,
            pytest_passed=pytest_passed,
        )
        details[criterion] = passed
        evidence.append(
            {
                "criterion": criterion,
                "passed": passed,
                "verification_method": method,
                "details": text,
            }
        )
        if not passed:
            misses.append(text)

    return {
        "details": details,
        "evidence": evidence,
        "misses": misses,
        "pytest_passed": pytest_passed,
        "collected_tests": collected,
        "pytest_returncode": outcome.returncode,
    }


def _collected_tests(returncode: int | None, junit_xml: str) -> bool:
    if returncode is None or returncode == 5:
        return False
    return "<testcase" in junit_xml


def _judge_criterion(
    workspace: str,
    criterion: str,
    *,
    passing_hits: Sequence[Any],
    pytest_passed: bool,
) -> tuple[bool, str, str]:
    numbers = expected_numbers(criterion)
    if numbers:
        missing = [
            number
            for number in numbers
            if not any(hit.value == number for hit in passing_hits)
        ]
        if missing:
            rendered = ", ".join(str(number) for number in missing)
            return (
                False,
                "pytest_assert",
                f"Expected value {rendered} was not asserted in a passing test",
            )
        return True, "pytest_assert", "Expected value asserted in a passing test"

    target = _file_existence_target(criterion)
    if target is not None:
        path = Path(workspace) / target
        if ".." in Path(target).parts:
            return False, "filesystem", f"Refusing to check unsafe path '{target}'"
        exists = path.is_file()
        if exists:
            return True, "filesystem", f"Verified '{target}' exists on disk"
        return False, "filesystem", f"Verified '{target}' is missing"

    if _is_pytest_criterion(criterion):
        if pytest_passed:
            return True, "pytest", "pytest passed"
        return False, "pytest", "pytest did not pass"

    return (
        False,
        "unverified",
        "No trusted behavioral verifier produced evidence",
    )


def _file_existence_target(criterion: str) -> str | None:
    match = _PY_FILE.search(criterion)
    if match is None:
        return None
    words = set(re.sub(r"[^a-z0-9]+", " ", criterion.lower()).split())
    if not words & _EXISTENCE_WORDS:
        return None
    return match.group(1)


def _is_pytest_criterion(criterion: str) -> bool:
    text = criterion.lower()
    return "pytest" in text or ("test" in text and "pass" in text)
