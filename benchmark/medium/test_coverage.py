"""Add tests to existing code."""

TASK = {
    "id": "medium_test_coverage",
    "category": "medium",
    "domain": "testing",
    "spec": (
        "Given `string_utils.py` with `slugify` and `truncate`, write thorough pytest tests in "
        "`test_string_utils.py` covering unicode, empty strings, and boundary lengths. "
        "Do not change production behavior unless a clear bug is found."
    ),
    "acceptance_criteria": [
        "test_string_utils.py exists",
        "tests cover empty and unicode inputs",
        "tests cover truncate boundary conditions",
        "pytest passes",
    ],
    "complexity_score": 0.45,
    "expected_cost": 0.15,
    "expected_time": 40,
    "difficulty": 2,
    "tags": ["python", "testing"],
    "seed_code": (
        "# string_utils.py\n"
        "def slugify(text: str) -> str:\n"
        "    return '-'.join(text.strip().lower().split())\n\n"
        "def truncate(text: str, n: int) -> str:\n"
        "    if n <= 0:\n"
        "        return ''\n"
        "    return text if len(text) <= n else text[: n - 1] + '…'\n"
    ),
}
