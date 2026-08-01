"""Class with methods."""

TASK = {
    "id": "easy_simple_class",
    "category": "easy",
    "spec": (
        "Create `counter.py` with a `Counter` class supporting increment(), decrement(), "
        "and value property (default start 0). Prevent value from going below 0 on decrement. "
        "Add unit tests in `test_counter.py`."
    ),
    "acceptance_criteria": [
        "Counter class exists in counter.py",
        "increment increases value by 1",
        "decrement decreases value by 1 but not below 0",
        "pytest test_counter.py passes",
    ],
    "complexity_score": 0.25,
    "expected_cost": 0.06,
    "expected_time": 20,
    "difficulty": 1,
    "tags": ["python", "oop", "pytest"],
}
