"""Feature across 2-3 files."""

TASK = {
    "id": "medium_multi_file_feature",
    "category": "medium",
    "domain": "backend",
    "spec": (
        "Implement a tiny user store across `models/user.py`, `services/user_service.py`, "
        "and `api/users.py` supporting create/get/list with basic email validation. "
        "Include pytest coverage for the service layer."
    ),
    "acceptance_criteria": [
        "User model has id, email, name fields",
        "create rejects invalid emails",
        "get returns None for missing ids",
        "list returns created users",
        "pytest passes for service tests",
    ],
    "complexity_score": 0.55,
    "expected_cost": 0.25,
    "expected_time": 60,
    "difficulty": 3,
    "tags": ["python", "backend", "multi-file"],
}
