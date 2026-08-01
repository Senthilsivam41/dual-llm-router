"""Single function, clear spec."""

TASK = {
    "id": "easy_simple_function",
    "category": "easy",
    "domain": "basic",
    "spec": (
        "Create a Python module `math_ops.py` with a function `factorial(n: int) -> int` "
        "that returns n!. Handle n=0 and n=1 as 1, and raise ValueError for negative n. "
        "Add `test_math_ops.py` with pytest coverage for those cases."
    ),
    "acceptance_criteria": [
        "math_ops.py exists and defines factorial",
        "factorial(0) == 1 and factorial(1) == 1",
        "factorial(5) == 120",
        "negative inputs raise ValueError",
        "pytest test_math_ops.py passes",
    ],
    "complexity_score": 0.2,
    "expected_cost": 0.05,
    "expected_time": 15,
    "difficulty": 1,
    "tags": ["python", "basic", "math", "pytest"],
    "seed_code": None,
    "expected_code": None,
}
