"""Guide task: file creation with greeting helper."""

TASK = {
    "id": "easy_file_creation",
    "category": "easy",
    "domain": "basic",
    "spec": (
        "Create a file 'greeting.py' with a function that returns a greeting message."
    ),
    "acceptance_criteria": [
        "File should be created at correct path",
        "Greeting function should return string",
        "Function should be callable",
    ],
    "complexity_score": 0.15,
    "expected_cost": 0.03,
    "expected_time": 8,
    "difficulty": 1,
    "tags": ["python", "file_creation", "basic"],
    "seed_code": None,
    "expected_code": None,
}
