"""Refactor architecture."""

TASK = {
    "id": "hard_architecture_change",
    "category": "hard",
    "domain": "architecture",
    "spec": (
        "Refactor a small monolith in `app/` into layers: `domain/`, `services/`, and `api/`, "
        "with dependency injection for the repository. Preserve existing CLI behavior and add "
        "unit tests for the service layer."
    ),
    "acceptance_criteria": [
        "Clear domain/service/api separation exists",
        "Repository is injected, not hardcoded in services",
        "No circular imports between layers",
        "Existing CLI entrypoint still works",
        "Service unit tests pass",
    ],
    "complexity_score": 0.85,
    "expected_cost": 0.7,
    "expected_time": 180,
    "difficulty": 5,
    "tags": ["python", "architecture", "refactor"],
}
