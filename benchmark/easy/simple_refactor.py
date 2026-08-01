"""Straightforward refactor."""

TASK = {
    "id": "easy_simple_refactor",
    "category": "easy",
    "domain": "refactor",
    "spec": (
        "Refactor the duplicated add logic in `legacy_calc.py` into a shared helper "
        "`add(a, b)` in `calc_utils.py`, update call sites, and keep behavior identical. "
        "Add/keep tests in `test_calc_utils.py`."
    ),
    "acceptance_criteria": [
        "calc_utils.py defines add(a, b)",
        "legacy_calc.py uses calc_utils.add",
        "behavior for sample inputs unchanged",
        "pytest passes",
    ],
    "complexity_score": 0.3,
    "expected_cost": 0.08,
    "expected_time": 25,
    "difficulty": 2,
    "tags": ["python", "refactor"],
    "seed_code": (
        "# legacy_calc.py\n"
        "def total(x, y):\n"
        "    return x + y\n\n"
        "def total3(a, b, c):\n"
        "    return a + b + c\n"
    ),
}
