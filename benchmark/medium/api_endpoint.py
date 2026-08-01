"""Guide task: CRUD REST API endpoint."""

TASK = {
    "id": "medium_api_endpoint",
    "category": "medium",
    "domain": "backend",
    "spec": (
        "Create a REST API endpoint that creates, reads, updates, and deletes (CRUD) "
        "user records with input validation."
    ),
    "acceptance_criteria": [
        "API should support GET /users",
        "API should support POST /users with validation",
        "API should support PUT /users/{id}",
        "API should support DELETE /users/{id}",
        "API should return 400 for invalid input",
        "API should return 404 for non-existent user",
        "API should return 200 for successful operations",
    ],
    "complexity_score": 0.6,
    "expected_cost": 0.30,
    "expected_time": 60,
    "difficulty": 3,
    "tags": ["python", "backend", "api", "crud"],
    "seed_code": None,
    "expected_code": None,
}