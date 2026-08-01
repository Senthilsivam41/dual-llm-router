"""Cross-service integration."""

TASK = {
    "id": "extreme_multi_service",
    "category": "extreme",
    "spec": (
        "Implement two local services (`orders` and `inventory`) that communicate over HTTP "
        "(or a lightweight in-process bus) to reserve stock when an order is created. Include "
        "idempotency keys, a failure/retry path, and integration tests."
    ),
    "acceptance_criteria": [
        "Order creation reserves inventory atomically or rolls back",
        "Idempotent retries do not double-reserve",
        "Inventory service failure surfaces a clear error",
        "Integration tests cover success and failure paths",
    ],
    "complexity_score": 0.97,
    "expected_cost": 1.3,
    "expected_time": 320,
    "difficulty": 5,
    "tags": ["python", "distributed", "integration"],
}
