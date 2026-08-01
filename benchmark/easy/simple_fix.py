"""Single bug fix."""

TASK = {
    "id": "easy_simple_fix",
    "category": "easy",
    "domain": "debugging",
    "spec": (
        "Fix the off-by-one bug in `greeter.py` so `greet_many(names)` joins names with "
        "commas correctly (no trailing comma). Keep `test_greeter.py` green."
    ),
    "acceptance_criteria": [
        "greet_many(['a']) == 'Hello a'",
        "greet_many(['a', 'b']) == 'Hello a, b'",
        "no trailing comma in output",
        "pytest test_greeter.py passes",
    ],
    "complexity_score": 0.2,
    "expected_cost": 0.05,
    "expected_time": 15,
    "difficulty": 1,
    "tags": ["python", "bugfix"],
    "seed_code": (
        "# greeter.py\n"
        "def greet_many(names):\n"
        "    out = 'Hello '\n"
        "    for i in range(len(names) + 1):\n"
        "        out += names[i]\n"
        "        if i < len(names):\n"
        "            out += ', '\n"
        "    return out\n"
    ),
}
