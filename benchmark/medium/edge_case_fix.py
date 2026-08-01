"""Fix with edge cases."""

TASK = {
    "id": "medium_edge_case_bug",
    "category": "medium",
    "spec": (
        "Fix `parse_csv_line(line)` in `csv_lite.py` so quoted commas and empty fields work. "
        "Add failing-first tests then make them pass."
    ),
    "acceptance_criteria": [
        "quoted commas stay inside a single field",
        "empty fields are preserved",
        "unquoted simple lines still split on commas",
        "pytest passes",
    ],
    "complexity_score": 0.55,
    "expected_cost": 0.2,
    "expected_time": 50,
    "difficulty": 3,
    "tags": ["python", "bugfix", "edge-cases"],
    "seed_code": (
        "# csv_lite.py\n"
        "def parse_csv_line(line: str):\n"
        "    return line.split(',')\n"
    ),
}
