"""Moderate logic."""

TASK = {
    "id": "medium_moderate_complexity",
    "category": "medium",
    "spec": (
        "Implement `scheduler.py` with `merge_intervals(intervals)` that merges overlapping "
        "[start, end] intervals and returns them sorted. Cover adjacent, nested, and empty cases "
        "in `test_scheduler.py`."
    ),
    "acceptance_criteria": [
        "merge_intervals merges overlapping ranges",
        "adjacent intervals are merged",
        "empty input returns []",
        "pytest test_scheduler.py passes",
    ],
    "complexity_score": 0.5,
    "expected_cost": 0.18,
    "expected_time": 45,
    "difficulty": 3,
    "tags": ["python", "algorithms"],
}
